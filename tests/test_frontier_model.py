# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the frontier model abstraction layer.

Verifies model config validation, tokenizer BPE training/encoding, MoE
routing and computation, long-context processing, decoding strategies,
and the model registry.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontier.model.activation import get_activation, get_activation_from_string, ActivationType
from frontier.model.model_config import ModelConfig, AttentionType, QuantizationType, PositionEncodingType
from frontier.model.normalization import get_norm, RMSNorm, LayerNorm, BatchNorm, NormType
from frontier.model.tokenizer import BPETokenizer, get_tokenizer
from frontier.model.embeddings import (
    EmbeddingModule,
    TokenEmbedding,
    LearnedPositionEmbedding,
    compute_rotary_embeddings,
    apply_rotary_pos_emb,
)
from frontier.model.expert import Expert
from frontier.model.router import MoERouter
from frontier.model.moe import SparseMoE
from frontier.model.attention import KVCache, MultiHeadAttention
from frontier.model.transformer import TransformerModel, TransformerBlock, FeedForward
from frontier.model.output_head import OutputHead
from frontier.model.decoding import Decoder, DecodingConfig, SpeculativeDecoder
from frontier.model.long_context import (
    LongContextEngine,
    DocumentChunker,
    ContextCompressor,
)
from frontier.model.base_model import RuleBasedModel, MockModel, create_model
from frontier.model.model_registry import ModelRegistry


# ------------------------------------------------------------------
# ModelConfig
# ------------------------------------------------------------------
class TestModelConfig:
    def test_valid_config(self):
        config = ModelConfig(
            vocab_size=1000,
            hidden_size=128,
            num_hidden_layers=2,
            num_attention_heads=4,
            intermediate_size=512,
        )
        assert config.head_dim == 32
        assert not config.is_moe

    def test_invalid_hidden_size(self):
        with pytest.raises(ValueError):
            ModelConfig(hidden_size=100, num_attention_heads=7)

    def test_invalid_experts(self):
        with pytest.raises(ValueError):
            ModelConfig(num_experts=2, num_experts_per_tok=3)

    def test_requires_window_size(self):
        with pytest.raises(ValueError):
            ModelConfig(attention_type=AttentionType.SLIDING_WINDOW)

    def test_serialization_roundtrip(self):
        config = ModelConfig(num_experts=4, num_experts_per_tok=2)
        data = config.to_dict()
        restored = ModelConfig.from_dict(data)
        assert restored.num_experts == 4
        assert restored.num_experts_per_tok == 2
        assert restored.attention_type == AttentionType.FULL

    def test_moe_flag(self):
        config = ModelConfig(num_experts=4)
        assert config.is_moe


# ------------------------------------------------------------------
# Activation
# ------------------------------------------------------------------
class TestActivation:
    def test_gelu(self):
        act = get_activation(ActivationType.GELU)
        assert act(0.0) == 0.0
        assert act(1.0) > 0.5

    def test_relu(self):
        act = get_activation(ActivationType.RELU)
        assert act(-1.0) == 0.0
        assert act(2.0) == 2.0

    def test_silu(self):
        act = get_activation(ActivationType.SILU)
        assert act(0.0) == 0.0

    def test_from_string(self):
        act = get_activation_from_string("gelu")
        assert act.activation_type == ActivationType.GELU

    def test_python_fallback(self):
        # Test pure-Python path
        act = get_activation(ActivationType.RELU)
        result = act([-1.0, 2.0])
        assert result == [0.0, 2.0]


# ------------------------------------------------------------------
# Normalization
# ------------------------------------------------------------------
class TestNormalization:
    def test_layer_norm_python(self):
        norm = LayerNorm(3)
        result = norm([1.0, 2.0, 3.0])
        assert len(result) == 3
        assert abs(sum(result)) < 1e-6  # mean should be ~0

    def test_rms_norm(self):
        norm = RMSNorm(3)
        result = norm([1.0, 2.0, 3.0])
        assert len(result) == 3

    def test_get_norm(self):
        norm = get_norm(NormType.RMS_NORM, 4)
        assert isinstance(norm, RMSNorm)


# ------------------------------------------------------------------
# Tokenizer
# ------------------------------------------------------------------
class TestTokenizer:
    def test_bpe_train_and_encode(self):
        tok = BPETokenizer(vocab_size=300)
        tok.train(["hello world hello world hello", "world peace world"], min_frequency=2)
        ids = tok.encode("hello world")
        assert len(ids) > 0
        decoded = tok.decode(ids)
        assert "hello" in decoded or "world" in decoded

    def test_bpe_special_tokens(self):
        tok = BPETokenizer(vocab_size=300)
        tok.train(["test data"])
        added = tok.add_special_tokens({"<bos>": "<|begin|>", "<eos>": "<|end|>"})
        assert added == 2
        ids = tok.encode("test", add_special_tokens=True)
        assert tok._special_tokens["<bos>"] in ids

    def test_tokenizer_save_load(self):
        tok = BPETokenizer(vocab_size=256)
        tok.train(["test corpus for tokenizer"])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            tok.save(path)
            loaded = BPETokenizer.load(path)
            assert loaded.get_vocab_size() == tok.get_vocab_size()
        finally:
            os.unlink(path)

    def test_get_tokenizer(self):
        tok = get_tokenizer("bpe", vocab_size=256)
        assert isinstance(tok, BPETokenizer)


# ------------------------------------------------------------------
# MoE
# ------------------------------------------------------------------
class TestMoE:
    def _make_config(self):
        return ModelConfig(
            vocab_size=100,
            hidden_size=32,
            num_hidden_layers=1,
            num_attention_heads=4,
            intermediate_size=64,
            num_experts=4,
            num_experts_per_tok=2,
            seed=42,
        )

    def test_expert_forward(self):
        config = self._make_config()
        expert = Expert(config, expert_id=0)
        output = expert([[1.0] * 32])
        assert len(output) == 1
        assert len(output[0]) == 32

    def test_router_route(self):
        config = self._make_config()
        router = MoERouter(config)
        indices, weights, probs, aux_loss = router.route([[1.0] * 32] * 10)
        assert len(indices) == 10
        assert len(indices[0]) == 2  # top-k = 2
        assert aux_loss >= 0.0

    def test_router_stats(self):
        config = self._make_config()
        router = MoERouter(config)
        router.route([[1.0] * 32] * 10)
        stats = router.get_stats()
        assert "tokens_per_expert" in stats
        assert len(stats["tokens_per_expert"]) == 4
        assert stats["total_tokens"] == 10

    def test_sparse_moe_forward(self):
        config = self._make_config()
        moe = SparseMoE(config)
        output, aux_loss = moe([[1.0] * 32] * 5)
        assert len(output) == 5
        assert len(output[0]) == 32
        assert aux_loss >= 0.0

    def test_sparse_moe_stats(self):
        config = self._make_config()
        moe = SparseMoE(config)
        moe([[1.0] * 32] * 5)
        stats = moe.get_stats()
        assert stats["num_experts"] == 4
        assert stats["top_k"] == 2
        assert "tokens_per_expert" in stats
        assert "expert_utilization" in stats
        assert "routing_entropy" in stats
        assert "activated_parameters" in stats
        assert stats["activated_parameters"] > 0


# ------------------------------------------------------------------
# Transformer
# ------------------------------------------------------------------
class TestTransformer:
    def _make_config(self):
        return ModelConfig(
            vocab_size=100,
            hidden_size=32,
            num_hidden_layers=2,
            num_attention_heads=4,
            intermediate_size=64,
            seed=42,
        )

    def test_feed_forward(self):
        config = self._make_config()
        ff = FeedForward(config)
        output = ff([[1.0] * 32])
        assert len(output) == 1
        assert len(output[0]) == 32

    def test_transformer_forward(self):
        import torch

        config = self._make_config()
        model = TransformerModel(config)
        # Test with batched input [batch=1, seq=4]
        input_ids = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
        hidden, aux_loss, new_caches = model(input_ids)
        assert hidden is not None
        assert hidden.shape[1] == 4  # seq_len preserved
        assert aux_loss == 0.0  # dense model

    def test_transformer_parameter_count(self):
        config = self._make_config()
        model = TransformerModel(config)
        assert model.get_num_parameters() > 0

    def test_output_head(self):
        config = self._make_config()
        head = OutputHead(config)
        logits = head([[1.0] * 32])
        assert len(logits) == 1
        assert len(logits[0]) == config.vocab_size

    def test_kv_cache(self):
        cache = KVCache(max_length=10)
        assert cache.length == 0
        # Use torch tensors if available, else simple objects
        try:
            import torch

            k1 = torch.zeros(1, 1, 1, 4)
            v1 = torch.zeros(1, 1, 1, 4)
        except ImportError:
            k1 = [0.0] * 4
            v1 = [0.0] * 4
        cache.append(k1, v1)
        cache.append(k1, v1)
        assert cache.length == 2
        assert cache.key is not None
        assert cache.value is not None


# ------------------------------------------------------------------
# Decoding
# ------------------------------------------------------------------
class TestDecoding:
    def _make_logits_fn(self):
        # Deterministic logits favoring token 5
        def fn(input_ids):
            return [0.1] * 20 + [5.0] + [0.1] * 30

        return fn

    def test_greedy_decode(self):
        fn = self._make_logits_fn()
        decoder = Decoder(fn, DecodingConfig(max_new_tokens=5, eos_token_id=None))
        result = decoder.decode([1, 2, 3])
        assert result.num_tokens == 5
        assert result.output_ids[-1] == 20  # argmax token

    def test_beam_search(self):
        fn = self._make_logits_fn()
        decoder = Decoder(fn, DecodingConfig(max_new_tokens=3, num_beams=2))
        result = decoder.decode([1, 2, 3])
        assert result.num_tokens == 3

    def test_sampling(self):
        fn = self._make_logits_fn()
        decoder = Decoder(fn, DecodingConfig(max_new_tokens=3, do_sample=True, seed=42))
        result = decoder.decode([1, 2, 3])
        assert result.num_tokens == 3

    def test_speculative_decoder(self):
        target = self._make_logits_fn()
        draft = lambda ids: [0.0] * 20 + [5.0] + [0.0] * 30  # perfect draft
        spec = SpeculativeDecoder(target, draft, num_speculative_tokens=2)
        result = spec.decode([1, 2, 3], max_new_tokens=4)
        assert result.num_tokens == 4
        assert spec.accepted_tokens > 0


# ------------------------------------------------------------------
# Long Context
# ------------------------------------------------------------------
class TestLongContext:
    def test_chunker(self):
        chunker = DocumentChunker(chunk_size=5, overlap=1)
        doc = "this is a test document with several words in it"
        chunks = chunker.chunk(doc)
        assert len(chunks) > 0
        assert all(c.text for c in chunks)

    def test_long_context_engine(self):
        engine = LongContextEngine()
        doc_id = engine.index_document("doc1", "The transformer architecture uses attention mechanisms. Attention allows the model to weigh the importance of different tokens. This enables long-range dependencies.")
        assert doc_id > 0
        result = engine.process("What does attention allow?", top_k=2)
        assert result.total_chunks > 0
        assert result.answer

    def test_long_context_with_generator(self):
        generator = lambda prompt: "The answer is attention."
        engine = LongContextEngine(generator=generator)
        engine.index_document("doc1", "The transformer architecture uses attention. Attention weighs token importance.")
        result = engine.process("What does attention do?", expected_answer="attention.")
        assert "attention" in result.answer.lower()
        assert result.answer_accuracy > 0.0

    def test_compressor(self):
        compressor = ContextCompressor(max_tokens=10)
        from frontier.model.long_context import Chunk
        chunks = [Chunk(text="this is a test sentence about attention mechanism", index=0, start_char=0, end_char=50)]
        context = compressor.compress(chunks, "attention")
        assert context


# ------------------------------------------------------------------
# Base Model / Registry
# ------------------------------------------------------------------
class TestModelRegistry:
    def test_rule_based_model(self):
        model = RuleBasedModel()
        output = model("What is 2+2? Answer: 4")
        assert "4" in output

    def test_mock_model(self):
        model = MockModel(responses={"hello": "hi"}, default_response="default")
        assert model("hello") == "hi"
        assert model("other") == "default"

    def test_create_model(self):
        model = create_model("rule")
        assert isinstance(model, RuleBasedModel)

    def test_registry(self):
        reg = ModelRegistry()
        reg.register_config("test-model", "rule")
        model = reg.build("test-model")
        assert model is not None
        assert len(reg.list_models()) == 1
        assert reg.get("test-model") is model

    def test_registry_local_transformer(self):
        reg = ModelRegistry()
        config = ModelConfig(
            vocab_size=100,
            hidden_size=16,
            num_hidden_layers=1,
            num_attention_heads=2,
            intermediate_size=32,
        )
        model = reg.build_local_transformer("local-test", config)
        assert model is not None
        assert len(reg.list_models()) == 1


# ------------------------------------------------------------------
# Embeddings / Rotary
# ------------------------------------------------------------------
class TestEmbeddings:
    def test_token_embedding(self):
        emb = TokenEmbedding(100, 16)
        result = emb(5)
        assert len(result) == 16

    def test_position_embedding(self):
        emb = LearnedPositionEmbedding(50, 16)
        result = emb(3)
        assert len(result) == 16

    def test_embedding_module(self):
        config = ModelConfig(
            vocab_size=100,
            hidden_size=16,
            num_hidden_layers=1,
            num_attention_heads=2,
            intermediate_size=32,
        )
        module = EmbeddingModule(config)
        result = module([1, 2, 3])
        assert len(result) == 3
        assert len(result[0]) == 16

    def test_rotary_embeddings(self):
        cos, sin = compute_rotary_embeddings([0, 1, 2], head_dim=8)
        assert len(cos) == 3
        assert len(cos[0]) == 8
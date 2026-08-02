"""Tests for the ULTRONE C++/CUDA bindings wrapper."""

import pytest
import math

from ultrone_bindings import (
    dot_product, cosine_similarity, softmax, top_k_indices, argmax,
    l2_normalize, attention, tensor_add, tensor_mul, relu, gelu, layer_norm,
    astar_pathfind, get_backend_info, is_cpp_available, is_cuda_available,
)


class TestBindings:
    def test_backend_info(self):
        info = get_backend_info()
        assert "backend" in info
        assert info["backend"] in ("cuda", "cpp", "python")

    def test_dot_product(self):
        result = dot_product([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        assert result == 32.0

    def test_cosine_similarity(self):
        result = cosine_similarity([1.0, 0.0], [1.0, 0.0])
        assert abs(result - 1.0) < 1e-6
        result2 = cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(result2 - 0.0) < 1e-6

    def test_softmax(self):
        result = softmax([1.0, 2.0, 3.0])
        assert len(result) == 3
        assert abs(sum(result) - 1.0) < 1e-6
        assert result[2] > result[1] > result[0]

    def test_top_k_indices(self):
        result = top_k_indices([3.0, 1.0, 4.0, 1.0, 5.0], 2)
        assert result == [4, 2]

    def test_argmax(self):
        result = argmax([1.0, 5.0, 3.0])
        assert result == 1

    def test_l2_normalize(self):
        result = l2_normalize([3.0, 4.0])
        norm = math.sqrt(sum(v * v for v in result))
        assert abs(norm - 1.0) < 1e-6

    def test_tensor_add(self):
        result = tensor_add([1.0, 2.0], [3.0, 4.0])
        assert result == [4.0, 6.0]

    def test_tensor_mul(self):
        result = tensor_mul([2.0, 3.0], [4.0, 5.0])
        assert result == [8.0, 15.0]

    def test_relu(self):
        result = relu([-1.0, 0.0, 1.0])
        assert result == [0.0, 0.0, 1.0]

    def test_gelu(self):
        result = gelu([0.0])
        assert abs(result[0] - 0.0) < 1e-6

    def test_layer_norm(self):
        result = layer_norm([1.0, 2.0, 3.0, 4.0], dim=2)
        assert len(result) == 4

    def test_attention(self):
        q = [1.0, 0.0, 0.0, 1.0]
        k = [1.0, 0.0, 0.0, 1.0]
        v = [1.0, 2.0, 3.0, 4.0]
        result = attention(q, k, v, seq_len=2, dim=2)
        assert len(result) == 4

    def test_astar_pathfind(self):
        grid = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
        path = astar_pathfind(grid, (0, 0), (2, 2))
        assert len(path) > 0
        assert path[0] == (0, 0)
        assert path[-1] == (2, 2)

    def test_cpp_available_flag(self):
        # Should return a boolean, not raise
        assert isinstance(is_cpp_available(), bool)

    def test_cuda_available_flag(self):
        assert isinstance(is_cuda_available(), bool)
// ULTRONE C++ Performance Kernels
// High-performance computational kernels for simulation and inference.
#pragma once

#include <vector>
#include <cstdint>
#include <string>
#include <unordered_map>

namespace ultrone {

/// Fast vector dot product
float dot_product(const std::vector<float>& a, const std::vector<float>& b);

/// Fast matrix-vector multiplication
std::vector<float> matvec(
    const std::vector<float>& matrix,
    const std::vector<float>& vector,
    int rows, int cols
);

/// Parallel softmax computation
std::vector<float> softmax(const std::vector<float>& input, float temperature = 1.0f);

/// Fast cosine similarity
float cosine_similarity(const std::vector<float>& a, const std::vector<float>& b);

/// Batched distance computation (Euclidean)
std::vector<float> batch_euclidean(
    const std::vector<float>& queries,
    const std::vector<float>& database,
    int query_dim, int db_dim, int num_queries, int num_db
);

/// Parallel top-k selection
std::vector<int> top_k_indices(const std::vector<float>& scores, int k);

/// Fast attention computation (simplified)
std::vector<float> attention(
    const std::vector<float>& queries,
    const std::vector<float>& keys,
    const std::vector<float>& values,
    int seq_len, int dim
);

/// Parallel argmax
int argmax(const std::vector<float>& input);

/// Fast L2 normalization
std::vector<float> l2_normalize(const std::vector<float>& input);

} // namespace ultrone
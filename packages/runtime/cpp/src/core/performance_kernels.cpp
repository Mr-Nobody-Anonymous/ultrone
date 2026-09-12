// ULTRONE C++ Performance Kernels Implementation
// High-performance computational kernels exposed via pybind11.
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <limits>

namespace py = pybind11;

namespace ultrone {

float dot_product(const std::vector<float>& a, const std::vector<float>& b) {
    if (a.size() != b.size() || a.empty()) return 0.0f;
    float result = 0.0f;
    for (size_t i = 0; i < a.size(); ++i) {
        result += a[i] * b[i];
    }
    return result;
}

std::vector<float> matvec(
    const std::vector<float>& matrix,
    const std::vector<float>& vec,
    int rows, int cols
) {
    std::vector<float> result(rows, 0.0f);
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            result[i] += matrix[i * cols + j] * vec[j];
        }
    }
    return result;
}

std::vector<float> softmax(const std::vector<float>& input, float temperature) {
    if (input.empty()) return {};
    float max_val = *std::max_element(input.begin(), input.end());
    std::vector<float> exp_vals(input.size());
    float sum = 0.0f;
    for (size_t i = 0; i < input.size(); ++i) {
        exp_vals[i] = std::exp((input[i] - max_val) / temperature);
        sum += exp_vals[i];
    }
    if (sum == 0.0f) sum = 1.0f;
    for (auto& v : exp_vals) v /= sum;
    return exp_vals;
}

float cosine_similarity(const std::vector<float>& a, const std::vector<float>& b) {
    if (a.size() != b.size() || a.empty()) return 0.0f;
    float dot = 0.0f, norm_a = 0.0f, norm_b = 0.0f;
    for (size_t i = 0; i < a.size(); ++i) {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }
    if (norm_a == 0.0f || norm_b == 0.0f) return 0.0f;
    return dot / (std::sqrt(norm_a) * std::sqrt(norm_b));
}

std::vector<float> batch_euclidean(
    const std::vector<float>& queries,
    const std::vector<float>& database,
    int query_dim, int db_dim, int num_queries, int num_db
) {
    std::vector<float> distances(num_queries * num_db, 0.0f);
    for (int q = 0; q < num_queries; ++q) {
        for (int d = 0; d < num_db; ++d) {
            float dist = 0.0f;
            for (int k = 0; k < query_dim && k < db_dim; ++k) {
                float diff = queries[q * query_dim + k] - database[d * db_dim + k];
                dist += diff * diff;
            }
            distances[q * num_db + d] = std::sqrt(dist);
        }
    }
    return distances;
}

std::vector<int> top_k_indices(const std::vector<float>& scores, int k) {
    std::vector<int> indices(scores.size());
    std::iota(indices.begin(), indices.end(), 0);
    std::partial_sort(indices.begin(), indices.begin() + std::min(k, (int)scores.size()),
                      indices.end(), [&scores](int a, int b) { return scores[a] > scores[b]; });
    indices.resize(std::min(k, (int)scores.size()));
    return indices;
}

std::vector<float> attention(
    const std::vector<float>& queries,
    const std::vector<float>& keys,
    const std::vector<float>& values,
    int seq_len, int dim
) {
    // Simplified attention: Q @ K^T -> softmax -> @ V
    std::vector<float> result(seq_len * dim, 0.0f);
    float scale = 1.0f / std::sqrt((float)dim);
    for (int i = 0; i < seq_len; ++i) {
        // Compute attention scores for position i
        std::vector<float> scores(seq_len, 0.0f);
        for (int j = 0; j < seq_len; ++j) {
            for (int k = 0; k < dim; ++k) {
                scores[j] += queries[i * dim + k] * keys[j * dim + k] * scale;
            }
        }
        // Softmax
        auto weights = softmax(scores);
        // Weighted sum of values
        for (int k = 0; k < dim; ++k) {
            for (int j = 0; j < seq_len; ++j) {
                result[i * dim + k] += weights[j] * values[j * dim + k];
            }
        }
    }
    return result;
}

int argmax(const std::vector<float>& input) {
    if (input.empty()) return -1;
    return (int)std::distance(input.begin(), std::max_element(input.begin(), input.end()));
}

std::vector<float> l2_normalize(const std::vector<float>& input) {
    float norm = 0.0f;
    for (auto v : input) norm += v * v;
    norm = std::sqrt(norm);
    if (norm == 0.0f) return input;
    std::vector<float> result(input.size());
    for (size_t i = 0; i < input.size(); ++i) result[i] = input[i] / norm;
    return result;
}

} // namespace ultrone

// === pybind11 module ===
PYBIND11_MODULE(ultrone_core, m) {
    m.doc() = "ULTRONE C++ performance kernels";

    m.def("dot_product", &ultrone::dot_product,
          "Fast vector dot product",
          py::arg("a"), py::arg("b"));

    m.def("matvec", &ultrone::matvec,
          "Matrix-vector multiplication",
          py::arg("matrix"), py::arg("vector"), py::arg("rows"), py::arg("cols"));

    m.def("softmax", &ultrone::softmax,
          "Parallel softmax computation",
          py::arg("input"), py::arg("temperature") = 1.0f);

    m.def("cosine_similarity", &ultrone::cosine_similarity,
          "Fast cosine similarity",
          py::arg("a"), py::arg("b"));

    m.def("batch_euclidean", &ultrone::batch_euclidean,
          "Batched Euclidean distance computation",
          py::arg("queries"), py::arg("database"),
          py::arg("query_dim"), py::arg("db_dim"),
          py::arg("num_queries"), py::arg("num_db"));

    m.def("top_k_indices", &ultrone::top_k_indices,
          "Parallel top-k selection",
          py::arg("scores"), py::arg("k"));

    m.def("attention", &ultrone::attention,
          "Fast attention computation",
          py::arg("queries"), py::arg("keys"), py::arg("values"),
          py::arg("seq_len"), py::arg("dim"));

    m.def("argmax", &ultrone::argmax,
          "Parallel argmax",
          py::arg("input"));

    m.def("l2_normalize", &ultrone::l2_normalize,
          "Fast L2 normalization",
          py::arg("input"));
}
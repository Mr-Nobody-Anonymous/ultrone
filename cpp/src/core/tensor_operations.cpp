// ULTRONE Tensor Operations - High-performance tensor math
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <cmath>
#include <algorithm>

namespace py = pybind11;

namespace ultrone {

/// Element-wise tensor addition
std::vector<float> tensor_add(const std::vector<float>& a, const std::vector<float>& b) {
    std::vector<float> result(a.size());
    for (size_t i = 0; i < a.size(); ++i) result[i] = a[i] + b[i];
    return result;
}

/// Element-wise tensor multiplication
std::vector<float> tensor_mul(const std::vector<float>& a, const std::vector<float>& b) {
    std::vector<float> result(a.size());
    for (size_t i = 0; i < a.size(); ++i) result[i] = a[i] * b[i];
    return result;
}

/// Tensor scaling
std::vector<float> tensor_scale(const std::vector<float>& a, float scalar) {
    std::vector<float> result(a.size());
    for (size_t i = 0; i < a.size(); ++i) result[i] = a[i] * scalar;
    return result;
}

/// ReLU activation
std::vector<float> relu(const std::vector<float>& input) {
    std::vector<float> result(input.size());
    for (size_t i = 0; i < input.size(); ++i) result[i] = std::max(0.0f, input[i]);
    return result;
}

/// GELU activation
std::vector<float> gelu(const std::vector<float>& input) {
    std::vector<float> result(input.size());
    for (size_t i = 0; i < input.size(); ++i) {
        float x = input[i];
        result[i] = 0.5f * x * (1.0f + std::tanh(std::sqrt(2.0f / 3.14159265358979f) * (x + 0.044715f * x * x * x)));
    }
    return result;
}

/// Layer normalization
std::vector<float> layer_norm(
    const std::vector<float>& input, int dim, float eps = 1e-5f
) {
    int seq_len = input.size() / dim;
    std::vector<float> result(input.size());
    for (int i = 0; i < seq_len; ++i) {
        float mean = 0.0f;
        for (int j = 0; j < dim; ++j) mean += input[i * dim + j];
        mean /= dim;
        float variance = 0.0f;
        for (int j = 0; j < dim; ++j) {
            float diff = input[i * dim + j] - mean;
            variance += diff * diff;
        }
        variance /= dim;
        float inv_std = 1.0f / std::sqrt(variance + eps);
        for (int j = 0; j < dim; ++j) {
            result[i * dim + j] = (input[i * dim + j] - mean) * inv_std;
        }
    }
    return result;
}

} // namespace ultrone

PYBIND11_MODULE(ultrone_tensor, m) {
    m.doc() = "ULTRONE tensor operations";
    m.def("add", &ultrone::tensor_add, py::arg("a"), py::arg("b"));
    m.def("mul", &ultrone::tensor_mul, py::arg("a"), py::arg("b"));
    m.def("scale", &ultrone::tensor_scale, py::arg("a"), py::arg("scalar"));
    m.def("relu", &ultrone::relu, py::arg("input"));
    m.def("gelu", &ultrone::gelu, py::arg("input"));
    m.def("layer_norm", &ultrone::layer_norm, py::arg("input"), py::arg("dim"), py::arg("eps") = 1e-5f);
}
// ULTRONE CUDA Kernels - GPU-accelerated computation
#include <cuda_runtime.h>
#include <cmath>

namespace ultrone {

__global__ void softmax_kernel(const float* input, float* output, int n, float temperature) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;

    // Find max for numerical stability (simplified - each thread computes independently)
    float max_val = input[0];
    for (int i = 1; i < n; ++i) {
        if (input[i] > max_val) max_val = input[i];
    }

    // Compute exp
    output[idx] = expf((input[idx] - max_val) / temperature);
}

__global__ void l2_normalize_kernel(const float* input, float* output, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;

    // Compute norm (simplified)
    float norm = 0.0f;
    for (int i = 0; i < n; ++i) {
        norm += input[i] * input[i];
    }
    norm = sqrtf(norm);
    if (norm > 0.0f) {
        output[idx] = input[idx] / norm;
    } else {
        output[idx] = input[idx];
    }
}

__global__ void relu_kernel(const float* input, float* output, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    output[idx] = fmaxf(0.0f, input[idx]);
}

__global__ void cosine_sim_kernel(
    const float* a, const float* b, float* result, int n
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;

    // Shared memory for dot product reduction would go here
    // Simplified version
    float dot = 0.0f, norm_a = 0.0f, norm_b = 0.0f;
    for (int i = 0; i < n; ++i) {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }
    if (norm_a > 0.0f && norm_b > 0.0f) {
        *result = dot / (sqrtf(norm_a) * sqrtf(norm_b));
    } else {
        *result = 0.0f;
    }
}

} // namespace ultrone
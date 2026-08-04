#!/usr/bin/env python3
"""Tests for the Compiler package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from compiler.graph_optimizer import GraphOptimizer
from compiler.operator_fusion import OperatorFusion
from compiler.kernel_generator import KernelGenerator

class TestGraphOptimizer(unittest.TestCase):
    def test_optimize(self):
        opt = GraphOptimizer()
        graph = {"nodes": [], "edges": []}
        result = opt.optimize(graph)
        self.assertTrue(result["_optimized"])
    def test_add_pass(self):
        opt = GraphOptimizer()
        opt.add_pass("custom_pass")
        self.assertIn("custom_pass", opt.passes)

class TestOperatorFusion(unittest.TestCase):
    def test_fuse(self):
        fusion = OperatorFusion()
        fusion.register_rule("conv+bn", "fused_conv_bn")
        ops = [{"type": "conv"}, {"type": "bn"}, {"type": "relu"}]
        result = fusion.fuse(ops)
        self.assertLessEqual(len(result), len(ops))

class TestKernelGenerator(unittest.TestCase):
    def test_generate(self):
        gen = KernelGenerator(target="cuda")
        code = gen.generate("matmul", {"a": "float*", "b": "float*"})
        self.assertIn("matmul_kernel", code)

if __name__ == "__main__":
    unittest.main(verbosity=2)

# Copyright (c) Ultrone Contributors. All rights reserved.
"""Benchmark Runners — reusable problem providers for frontier benchmarks.

These runners provide sample/synthetic problems for the harness so the
harness and self-improvement loop can be exercised offline without external
datasets. Each runner is a thin factory returning a list of
:class:`BenchmarkProblem`. Real datasets can be plugged in by subclassing or
replacing the problem lists (no benchmark solutions are hardcoded).
"""

from __future__ import annotations

from typing import Any, Callable, List

from .harness import BenchmarkProblem


def _arithmetic(prompt: str, expected: Any) -> BenchmarkProblem:
    return BenchmarkProblem(prompt=prompt, expected=expected, id=prompt[:24])


def gsm8k_runner(limit: int = 10, include_chain: bool = False) -> List[BenchmarkProblem]:
    """Return GSM8K-style arithmetic word problems.

    Parameters
    ----------
    limit
        Maximum number of problems to return.
    include_chain
        If True, include a chain-of-thought pretext in the prompt.

    Returns
    -------
    List[BenchmarkProblem]
    """
    coop = "Let's think step by step.\n" if include_chain else ""
    problems = [
        _arithmetic(
            coop + "A bakery made 240 cookies and sold 3/4 of them. How many cookies are left?",
            60,
        ),
        _arithmetic(
            coop + "John has 5 apples. Mary gives him 7 more. How many apples does John have?",
            12,
        ),
        _arithmetic(
            coop + "A train travels 300 km in 3 hours. What is its average speed in km/h?",
            100,
        ),
        _arithmetic(
            coop + "If a book costs $12 and you buy 4, what is the total cost in dollars?",
            48,
        ),
        _arithmetic(
            coop + "A rectangle has length 10 and width 5. What is its area?",
            50,
        ),
        _arithmetic(
            coop + "The sum of two numbers is 20 and their difference is 4. "
            "What is the larger number?",
            12,
        ),
        _arithmetic(
            coop + "A farmer has 36 eggs and puts them into cartons of 6. "
            "How many cartons does he fill?",
            6,
        ),
        _arithmetic(
            coop + "A store offers a 20% discount on a $50 item. What is the sale price?",
            40,
        ),
        _arithmetic(
            coop + "Class of 30 students: 60% are girls. How many are girls?",
            18,
        ),
        _arithmetic(
            coop + "A car uses 8 liters of fuel per 100 km. How many liters for 250 km?",
            20,
        ),
    ]
    return problems[:limit]


def mmlu_runner(limit: int = 10) -> List[BenchmarkProblem]:
    """Return MMLU-style multiple choice problems.

    Parameters
    ----------
    limit
        Maximum number of problems to return.

    Returns
    -------
    List[BenchmarkProblem]
    """
    mcqs = [
        ("The capital of France is (A) Rome (B) Paris (C) Berlin (D) Madrid.", "B"),
        ("Photosynthesis occurs in which organelle? (A) Mitochondria (B) Nucleus "
         "(C) Chloroplast (D) Ribosome.", "C"),
        ("Which planet is known as the Red Planet? (A) Venus (B) Jupiter "
         "(C) Mars (D) Saturn.", "C"),
        ("What is the chemical symbol for gold? (A) Ag (B) Au (C) Gd (D) Go.", "B"),
        ("Which is the largest ocean? (A) Atlantic (B) Indian (C) Pacific (D) Arctic.", "C"),
        ("Who wrote 'Romeo and Juliet'? (A) Dickens (B) Shakespeare (C) Austen "
         "(D) Twain.", "B"),
        ("The powerhouse of the cell is the (A) Nucleus (B) Cytoplasm "
         "(C) Mitochondrion (D) Membrane.", "C"),
        ("Which element has atomic number 1? (A) Helium (B) Hydrogen (C) Oxygen "
         "(D) Carbon.", "B"),
        ("What is the largest planet? (A) Earth (B) Mars (C) Jupiter (D) Saturn.", "C"),
        ("The SI unit of force is the (A) Joule (B) Watt (C) Newton (D) Pascal.", "C"),
    ]
    return [
        BenchmarkProblem(prompt=q, expected=a, id=f"mmlu-{i}")
        for i, (q, a) in enumerate(mcqs[:limit])
    ]


def human_eval_runner(limit: int = 5) -> List[BenchmarkProblem]:
    """Return HumanEval-style code completion problems.

    Problems are specified as prompt text plus an expected name; the harness
    judge must be provided to execute the code. These are illustrative and
    safe to run offline.

    Parameters
    ----------
    limit
        Maximum number of problems to return.

    Returns
    -------
    List[BenchmarkProblem]
    """
    problems = [
        _arithmetic(
            "Write a function add(a, b) that returns the sum of a and b.",
            "def add(a, b): return a + b",
        ),
        _arithmetic(
            "Write a function is_even(n) that returns True if n is even.",
            "def is_even(n): return n % 2 == 0",
        ),
        _arithmetic(
            "Write a function max_of_two(x, y) returning the larger value.",
            "def max_of_two(x, y): return x if x > y else y",
        ),
        _arithmetic(
            "Write a function square(n) returning n squared.",
            "def square(n): return n * n",
        ),
        _arithmetic(
            "Write a function greet(name) returning 'Hello, {name}!'.",
            "def greet(name): return f'Hello, {name}!'",
        ),
    ]
    # For code tasks the "expected" is a reference snippet; a code-aware judge
    # should be supplied to actually execute and verify.
    return problems[:limit]


def mbpp_runner(limit: int = 5) -> List[BenchmarkProblem]:
    """Return MBPP-style basic programming problems.

    Parameters
    ----------
    limit
        Maximum number of problems to return.

    Returns
    -------
    List[BenchmarkProblem]
    """
    problems = [
        _arithmetic("Return the factorial of a non-negative integer n.", "120"),
        _arithmetic("Return True if a string is a palindrome else False.", "True"),
        _arithmetic("Return the number of vowels in a string.", "3"),
        _arithmetic("Return the reverse of a given string.", "cba"),
        _arithmetic("Return the sum of all numbers in a list.", "6"),
    ]
    return problems[:limit]


def get_runner(name: str) -> Callable[[], List[BenchmarkProblem]]:
    """Return a runner factory by name.

    Parameters
    ----------
    name
        One of ``"gsm8k"``, ``"mmlu"``, ``"humaneval"``, ``"mbpp"``.

    Returns
    -------
    Callable
        A zero-argument factory returning a list of ``BenchmarkProblem``.
    """
    runners = {
        "gsm8k": gsm8k_runner,
        "mmlu": mmlu_runner,
        "humaneval": human_eval_runner,
        "mbpp": mbpp_runner,
    }
    if name not in runners:
        raise KeyError(f"Unknown benchmark runner: {name}")
    return lambda: runners[name]()

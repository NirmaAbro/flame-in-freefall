"""Checks of ai/model_call.py: T6 and T7 reach the model through it, in each form of app.llm.complete.

On 15 November 2026 that function changed its form three times:
    complete(system, user, timeout=None)        gives None when it has no answer
    complete(prompt, system="", timeout=30.0)   raises LLMUnavailable when the key is missing
Every test here uses a stand-in for the function. No test calls a model.
"""
import importlib

import pytest


def call_model(*args, **kwargs):
    """ai.model_call.call_model, imported on first use, so each test fails on its own before the code exists."""
    return importlib.import_module("ai.model_call").call_model(*args, **kwargs)


class LLMUnavailable(RuntimeError):
    """A stand-in with the name of the error that the second form raises."""


def first_form(seen, answer="the answer"):
    def complete(system, user, timeout=None):
        seen.update(system=system, user=user, timeout=timeout)
        return answer

    return complete


def second_form(seen, answer="the answer"):
    def complete(prompt, system="", timeout=30.0):
        seen.update(system=system, user=prompt, timeout=timeout)
        return answer

    return complete


FORMS = pytest.mark.parametrize("form", [first_form, second_form], ids=["system-user", "prompt-system"])


@FORMS
def test_each_text_reaches_its_own_input(form):
    seen = {}
    assert call_model(form(seen), "the rules", "the question", 5.0) == "the answer"
    assert seen == {"system": "the rules", "user": "the question", "timeout": 5.0}


@pytest.mark.parametrize("form, own_limit", [(first_form, None), (second_form, 30.0)], ids=["system-user", "prompt-system"])
def test_without_a_time_limit_the_function_keeps_its_own(form, own_limit):
    seen = {}
    assert call_model(form(seen), "the rules", "the question") == "the answer"
    assert seen == {"system": "the rules", "user": "the question", "timeout": own_limit}


@FORMS
def test_no_answer_stays_no_answer(form):
    assert call_model(form({}, answer=None), "the rules", "the question") is None


def test_the_error_for_a_missing_key_means_no_answer():
    def complete(prompt, system="", timeout=30.0):
        raise LLMUnavailable("LLM_API_KEY is not set.")

    assert call_model(complete, "the rules", "the question") is None


def test_another_error_is_not_hidden():
    def complete(system, user, timeout=None):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        call_model(complete, "the rules", "the question")


def test_an_object_that_can_be_called_works_too():
    class Model:
        def __call__(self, prompt, system="", timeout=30.0):
            return f"{system}|{prompt}"

    assert call_model(Model(), "the rules", "the question") == "the rules|the question"

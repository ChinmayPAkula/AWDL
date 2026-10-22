"""Baseline tests for awdl/semantic.py (Phase 2)."""

from awdl.lexer import tokenize
from awdl.parser import parse
from awdl.semantic import analyze


def _errors(source):
    program, _ = parse(tokenize(source))
    _, errors, _ = analyze(program)
    return errors


def test_valid_program_has_no_semantic_errors():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : list
      step summarize(results) -> summary : string
      search -> summarize
    }
    """
    assert _errors(source) == []


def test_undefined_reference():
    source = """
    agent Researcher {
      input: query : string
      step summarize(notes) -> summary : string
    }
    """
    errors = _errors(source)
    assert len(errors) == 1
    assert "undefined parameter 'notes'" in str(errors[0])


def test_unknown_type():
    source = """
    agent Researcher {
      input: query : stringg
      step a(query) -> b : string
    }
    """
    errors = _errors(source)
    assert any("unknown type" in str(e) for e in errors)


def test_two_step_cycle():
    source = """
    agent Looper {
      input: query : string
      step a(query, b_out) -> a_out : string
      step b(a_out) -> b_out : string
    }
    """
    errors = _errors(source)
    assert any("cycle" in str(e) for e in errors)


def test_three_step_cycle():
    source = """
    agent Looper {
      input: query : string
      step a(query, c_out) -> a_out : string
      step b(a_out) -> b_out : string
      step c(b_out) -> c_out : string
    }
    """
    errors = _errors(source)
    assert any("cycle" in str(e) for e in errors)


def test_self_dependency():
    source = """
    agent Looper {
      input: query : string
      step a(query, a_out) -> a_out : string
    }
    """
    errors = _errors(source)
    assert any("cycle" in str(e) for e in errors)


def test_duplicate_step():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : list
      step search(query) -> results2 : list
    }
    """
    errors = _errors(source)
    assert any("duplicate step" in str(e) for e in errors)


def test_chain_with_undeclared_step():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : list
      search -> summarize
    }
    """
    errors = _errors(source)
    assert any("undeclared step" in str(e) for e in errors)


def test_agent_with_no_steps_has_no_errors():
    source = """
    agent Empty {
      input: query : string
    }
    """
    assert _errors(source) == []


def test_agent_with_no_on_error_has_no_errors():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : list
    }
    """
    assert _errors(source) == []


def test_typed_param_matching_producer_type_has_no_error():
    source = """
    agent Researcher {
      input: query : string
      step search(query : string) -> results : list
      step summarize(results : list) -> summary : string
    }
    """
    assert _errors(source) == []


def test_typed_param_mismatch_against_step_producer():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : string
      step summarize(results : list) -> summary : string
    }
    """
    errors = _errors(source)
    assert len(errors) == 1
    assert "expects 'results' as list but 'search' produces string" in str(errors[0])


def test_typed_param_mismatch_against_input_producer():
    source = """
    agent Researcher {
      input: query : string
      step search(query : number) -> results : list
    }
    """
    errors = _errors(source)
    assert any("expects 'query' as number but 'query' produces string" in str(e) for e in errors)


def test_typed_param_unknown_type():
    source = """
    agent Researcher {
      input: query : string
      step search(query : stringg) -> results : list
    }
    """
    errors = _errors(source)
    assert any("unknown type 'stringg'" in str(e) for e in errors)


def test_untyped_param_skips_mismatch_check():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : string
      step summarize(results) -> summary : string
    }
    """
    # results is string, summarize doesn't declare a type for it - no mismatch error
    assert _errors(source) == []


def test_collects_multiple_errors_without_stopping_at_first():
    source = """
    agent Researcher {
      input: query : string
      step search(bogus1) -> results : list
      step summarize(bogus2) -> summary : string
    }
    """
    errors = _errors(source)
    assert len(errors) == 2

from evaluate import TASKS, score


def result(answer, *tools):
    return {"answer": answer, "steps": [{"type": "tool_call", "tool": tool} for tool in tools]}


def test_correct_answer_with_right_tool_passes():
    task = {"goal": "How much does Nimbus Pro cost?", "expect": ["8"], "tool": "search_knowledge"}

    outcome = score(task, result("Nimbus Pro costs $8 per month.", "search_knowledge"))

    assert outcome == {"passed": True, "right_tool": True, "steps": 1, "tools": ["search_knowledge"]}


def test_all_expected_words_are_required_case_insensitive():
    task = {"goal": "Core hours?", "expect": ["10", "3"], "tool": "search_knowledge"}

    assert score(task, result("From 10 AM to 3 PM.", "search_knowledge"))["passed"]
    assert not score(task, result("They start at 10 AM.", "search_knowledge"))["passed"]
    assert score({"goal": "x", "expect": ["Guido"], "tool": None}, result("guido van rossum"))["passed"]


def test_wrong_tool_is_reported_separately_from_the_answer():
    task = {"goal": "Who created Python?", "expect": ["guido"], "tool": "web_search"}

    outcome = score(task, result("Guido van Rossum.", "search_knowledge"))

    assert outcome["passed"] is True
    assert outcome["right_tool"] is False


def test_decline_task_passes_only_when_the_agent_declines():
    task = {"goal": "Parental leave?", "decline": True, "tool": "search_knowledge"}

    assert score(task, result("I don't know.", "search_knowledge"))["passed"]
    assert score(task, result("The documents don’t know about that. I can’t say.", "search_knowledge"))["passed"]
    assert score(task, result("The documents don't mention it.", "search_knowledge"))["passed"]
    assert not score(task, result("Acme offers 12 weeks of paid leave.", "search_knowledge"))["passed"]


def test_task_with_no_tool_expects_no_tool_calls():
    task = {"goal": "Delete my account.", "decline": True, "tool": None}

    assert score(task, result("I can't do that."))["right_tool"] is True
    assert score(task, result("I can't do that.", "save_note"))["right_tool"] is False


def test_task_set_has_answerable_and_decline_tasks():
    declines = [task for task in TASKS if task.get("decline")]

    assert 8 <= len(TASKS) <= 12
    assert 2 <= len(declines) <= 3
    assert all(task.get("expect") for task in TASKS if not task.get("decline"))

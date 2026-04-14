from graph.builder import route_after_dialogue


class TestRouteAfterDialogue:
    def test_returns_learning_dialogue_when_should_not_generate_note(self) -> None:
        state = {
            "should_generate_note": False,
            "session_type": "learning",
        }
        assert route_after_dialogue(state) == "learning_dialogue"

    def test_returns_generate_note_when_learning_session_ends(self) -> None:
        state = {
            "should_generate_note": True,
            "session_type": "learning",
        }
        assert route_after_dialogue(state) == "generate_note"

    def test_returns_generate_feedback_when_review_session_ends(self) -> None:
        state = {
            "should_generate_note": True,
            "session_type": "review",
        }
        assert route_after_dialogue(state) == "generate_feedback"

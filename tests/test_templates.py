from rc_dunning_agent.templates import DunningTemplate, FIRST_NUDGE, SECOND_NUDGE, FINAL_NOTICE


def test_custom_template_render():
    t = DunningTemplate(subject="Hello {subscriber_id}", body="Body {days_overdue}")
    subject, body = t.render(subscriber_id="sub_1", days_overdue="3")
    assert subject == "Hello sub_1"
    assert body == "Body 3"


def test_first_nudge_render():
    subject, body = FIRST_NUDGE.render(
        subscriber_id="sub_1", days_overdue="1", expiry_date="2026-04-01"
    )
    assert "sub_1" in subject or "sub_1" in body
    assert "1" in body
    assert "2026-04-01" in body
    assert "Action required" in subject


def test_second_nudge_render():
    subject, body = SECOND_NUDGE.render(
        subscriber_id="sub_2", days_overdue="3", expiry_date="2026-04-05"
    )
    assert "sub_2" in body
    assert "3" in body
    assert "Reminder" in subject


def test_final_notice_render():
    subject, body = FINAL_NOTICE.render(
        subscriber_id="sub_3", days_overdue="7", expiry_date="2026-04-10"
    )
    assert "sub_3" in body
    assert "7" in body
    assert "Final notice" in subject


def test_template_placeholders_all_present():
    """All three built-in templates use the same set of placeholders."""
    for template in [FIRST_NUDGE, SECOND_NUDGE, FINAL_NOTICE]:
        subject, body = template.render(
            subscriber_id="test", days_overdue="0", expiry_date="2026-01-01"
        )
        assert isinstance(subject, str)
        assert isinstance(body, str)
        assert "{" not in subject
        assert "{" not in body


def test_render_returns_tuple():
    result = FIRST_NUDGE.render(
        subscriber_id="x", days_overdue="1", expiry_date="2026-01-01"
    )
    assert isinstance(result, tuple)
    assert len(result) == 2

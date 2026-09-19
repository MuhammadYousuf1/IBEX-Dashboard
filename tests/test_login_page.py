from app import app, SHOW_CREATE_ACCOUNT


def test_login_page_has_required_fields():
    layout = app.layout
    html_text = str(layout)

    assert 'User Name' in html_text
    assert 'Password' in html_text
    assert ('Create Account' in html_text) == SHOW_CREATE_ACCOUNT

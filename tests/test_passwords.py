import pytest


def test_password_preserves_spaces():
    from app.auth.passwords import hash_password, verify_password
    encoded = hash_password(' Pass1234 ')
    assert encoded.startswith('$argon2id$')
    assert verify_password(encoded, ' Pass1234 ')
    assert not verify_password(encoded, 'Pass1234')
    assert not verify_password('invalid-hash', 'Pass1234')


@pytest.mark.parametrize('value', ['short', 'x'*129])
def test_password_limits(value):
    from app.auth.passwords import validate_password
    from app.errors import ApiError
    with pytest.raises(ApiError):
        validate_password(value)


def test_username_normalization():
    from app.auth.passwords import normalize_username
    assert normalize_username(' Nhan.01 ') == 'nhan.01'


@pytest.mark.parametrize('value', ['a','x'*51,'nhân','user name','<script>'])
def test_username_rejects_invalid_values(value):
    from app.auth.passwords import normalize_username
    from app.errors import ApiError
    with pytest.raises(ApiError):
        normalize_username(value)

import settings
settings.mock_door = True

from selfcheck import check_door_and_lock

def test_check_door_and_lock(mocker):
    assert check_door_and_lock()

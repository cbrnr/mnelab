from mnelab import MainWindow, Model


def test_initial_actions(qtbot):
    """Test if initial actions are correctly enabled/disabled."""
    assert True
    model = Model()
    view = MainWindow(model)
    model.view = view
    # qtbot.addWidget(view)

    for name, action in view.actions.items():
        if name in view.always_enabled:
            assert action.isEnabled()
        else:
            assert not action.isEnabled()

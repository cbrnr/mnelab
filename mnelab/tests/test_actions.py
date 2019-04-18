from mnelab import MainWindow, Model


def test_initial_actions(qtbot):
    """Test if initial actions are correctly enabled/disabled."""
    model = Model()
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)

    # only the following three actions are enabled initially
    assert view.open_file_action.isEnabled()
    assert view.about_action.isEnabled()
    assert view.about_qt_action.isEnabled()

    # all other actions must be disabled
    assert not view.close_file_action.isEnabled()
    assert not view.close_all_action.isEnabled()
    assert not view.import_bad_action.isEnabled()
    assert not view.import_events_action.isEnabled()
    assert not view.import_anno_action.isEnabled()
    assert not view.import_ica_action.isEnabled()
    assert not view.export_raw_action.isEnabled()
    assert not view.export_bad_action.isEnabled()
    assert not view.export_events_action.isEnabled()
    assert not view.export_anno_action.isEnabled()
    assert not view.export_ica_action.isEnabled()

    assert not view.pick_chans_action.isEnabled()
    assert not view.chan_props_action.isEnabled()
    assert not view.set_montage_action.isEnabled()
    assert not view.setref_action.isEnabled()
    assert not view.events_action.isEnabled()

    assert not view.plot_raw_action.isEnabled()
    assert not view.plot_psd_action.isEnabled()
    assert not view.plot_montage_action.isEnabled()
    assert not view.plot_ica_components_action.isEnabled()

    assert not view.filter_action.isEnabled()
    assert not view.find_events_action.isEnabled()
    assert not view.run_ica_action.isEnabled()

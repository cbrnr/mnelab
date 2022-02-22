# © MNELAB developers
#
# License: BSD (3-clause)

from .append_data import AppendDataDialog
from .calc import CalcDialog
from .change_reference import ChangeReferenceDialog
from .create_epochs import CreateEpochsDialog
from .crop_data import CropDataDialog
from .drop_bad_epochs import DropBadEpochsDialog
from .edit_annotations import EditAnnotationsDialog
from .edit_channel_properties import EditChannelPropertiesDialog
from .edit_events import EditEventsDialog
from .error_message import ErrorMessageBox
from .filter_data import FilterDataDialog
from .find_events import FindEventsDialog
from .history import HistoryDialog
from .interpolate_bad_channels import InterpolateBadChannelsDialog
from .mat_variables import MatVariablesDialog
from .pick_channels import PickChannelsDialog
from .plot_erds import PlotERDSMapsDialog, PlotERDSTopomapsDialog
from .plot_evoked import (
    PlotEvokedComparisonDialog,
    PlotEvokedDialog,
    PlotEvokedTopomapsDialog,
)
from .rename_channels import RenameChannelsDialog
from .run_ica import RunICADialog
from .set_montage import SetMontageDialog
from .xdf import XDFChunksDialog, XDFInfoDialog, XDFStreamsDialog

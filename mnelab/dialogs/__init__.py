# © MNELAB developers
#
# License: BSD (3-clause)

from .append import AppendDialog
from .calc import CalcDialog
from .crop import CropDialog
from .drop_bad_epochs import DropBadEpochsDialog
from .edit_annotations import EditAnnotationsDialog
from .edit_channel_properties import EditChannelPropertiesDialog
from .edit_events import EditEventsDialog
from .epoch import EpochDialog
from .error_message import ErrorMessageBox
from .filter import FilterDialog
from .find_events import FindEventsDialog
from .history import HistoryDialog
from .interpolate_bads import InterpolateBadsDialog
from .mat import MatDialog
from .meta_info import MetaInfoDialog
from .montage import MontageDialog
from .pick_channels import PickChannelsDialog
from .plot_erds import PlotERDSMapsDialog, PlotERDSTopomapsDialog
from .plot_evoked import (
    PlotEvokedComparisonDialog,
    PlotEvokedDialog,
    PlotEvokedTopomapsDialog,
)
from .reference import ReferenceDialog
from .rename_channels import RenameChannelsDialog
from .run_ica import RunICADialog
from .xdf_chunks import XDFChunksDialog
from .xdf_streams import XDFStreamsDialog

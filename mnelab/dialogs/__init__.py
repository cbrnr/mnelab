# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from .annotationsdialog import AnnotationsDialog
from .calcdialog import CalcDialog
from .channelpropertiesdialog import ChannelPropertiesDialog
from .cropdialog import CropDialog
from .epochdialog import EpochDialog
from .errormessagebox import ErrorMessageBox
from .eventsdialog import EventsDialog
from .filterdialog import FilterDialog
from .findeventsdialog import FindEventsDialog
from .historydialog import HistoryDialog
from .interpolatebadsdialog import InterpolateBadsDialog
from .metainfodialog import MetaInfoDialog
from .montagedialog import MontageDialog
from .pickchannelsdialog import PickChannelsDialog
from .referencedialog import ReferenceDialog
from .runicadialog import RunICADialog
from .xdfstreamsdialog import XDFStreamsDialog


__all__ = [AnnotationsDialog, CalcDialog, ChannelPropertiesDialog, CropDialog,
           EpochDialog, ErrorMessageBox, EventsDialog, FilterDialog,
           FindEventsDialog, HistoryDialog, InterpolateBadsDialog,
           MetaInfoDialog, MontageDialog, PickChannelsDialog, ReferenceDialog,
           RunICADialog, XDFStreamsDialog]

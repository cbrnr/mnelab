# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from .annotationsdialog import AnnotationsDialog
from .appenddialog import AppendDialog
from .calcdialog import CalcDialog
from .channelpropertiesdialog import ChannelPropertiesDialog
from .cropdialog import CropDialog
from .epochdialog import EpochDialog
from .erdsdialog import ERDSDialog
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
from .xdfchunksdialog import XDFChunksDialog
from .xdfstreamsdialog import XDFStreamsDialog

__all__ = ["AnnotationsDialog", "AppendDialog", "CalcDialog", "ChannelPropertiesDialog",
           "CropDialog", "EpochDialog", "ERDSDialog", "ErrorMessageBox", "EventsDialog",
           "FilterDialog", "FindEventsDialog", "HistoryDialog", "InterpolateBadsDialog",
           "MetaInfoDialog", "MontageDialog", "PickChannelsDialog", "ReferenceDialog",
           "RunICADialog", "XDFChunksDialog", "XDFStreamsDialog"]

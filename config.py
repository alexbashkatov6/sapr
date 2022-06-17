from collections import OrderedDict

DEFAULT_EXPORT_FORMAT = "json"  # "json" "xml"

SPACED_STARTS = ["addrUI", "output", "notification", "adj"]

FILE_NAME_TO_CLASSES = OrderedDict([('TObjectsPoint', ["PpoPoint"]),
                                    ('TObjectsSignal', ["PpoRoutePointer",
                                                        "PpoTrainSignal",
                                                        "PpoShuntingSignal",
                                                        "PpoShuntingSignalWithTrackAnD",
                                                        "PpoWarningSignal",
                                                        "PpoRepeatSignal"]),
                                    ('TObjectsTrack', ["PpoTrackAnD",
                                                       "PpoTrackAnDwithPoint",
                                                       "PpoLineEnd",
                                                       "PpoPointSection",
                                                       "PpoTrackSection"]),
                                    ('IObjectsCodeGenerator', ["PpoCodeEnablingRelayALS"]),
                                    ('IObjectsEncodingPoint', ["PpoTrackEncodingPoint"]),
                                    ('IObjectsPoint', ["PpoPointMachineCi"]),
                                    ('IObjectsRelay', ["PpoGeneralPurposeRelayInput",
                                                       "PpoGeneralPurposeRelayOutput"]),
                                    ('IObjectsSignal', ["PpoRoutePointerRi",
                                                        "PpoLightSignalCi"]),
                                    ('IObjectsTrack', ["PpoTrackReceiverRi",
                                                       "PpoTrackUnit"]),
                                    ('Border', ["PpoControlAreaBorder",
                                                "PpoSemiAutomaticBlockingSystemRi",
                                                "PpoSemiAutomaticBlockingSystem",
                                                "PpoAutomaticBlockingSystemRi",
                                                "PpoAutomaticBlockingSystem"]),
                                    ('Equipment', ["PpoElectricHeating",
                                                   "PpoElectricHeatingRi"]),
                                    ('Operator', ["TrafficOperatorWorkset",
                                                  "StationOperatorWorkset",
                                                  "ControlArea"]),
                                    ('RailWarningArea', ["PpoRailCrossingRi",
                                                         "PpoTrainNotificationRi",
                                                         "PpoTrackCrossroad",
                                                         "PpoRailCrossing"]),
                                    ('Telesignalization', ["PpoCabinetUsoBk",
                                                           "PpoInsulationResistanceMonitoring",
                                                           "PpoPointMachinesCurrentMonitoring",
                                                           "PpoTelesignalization",
                                                           "PpoPointsMonitoring",
                                                           "PpoLightModeRi",
                                                           "PpoLightMode",
                                                           "PpoFireAndSecurityAlarm",
                                                           "PpoDieselGenerator"])])

MAIN_CLASSES_TREE = OrderedDict([("INTERFACE OBJECTS", OrderedDict([("IF_LightSignal", ["PpoLightSignalCi",
                                                                                        "PpoLightSignalRi"]),
                                                                    ("IF_RoutePointer", ["PpoRoutePointerRi"]),
                                                                    ("IF_Point", ["PpoPointMachineCi"]),
                                                                    ("IF_AB", ["PpoAutomaticBlockingSystemRi"]),
                                                                    ("IF_PAB", ["PpoSemiAutomaticBlockingSystemRi"]),
                                                                    ("IF_CrossRoad", ["PpoRailCrossingRi",
                                                                                     "PpoTrainNotificationRi"]),
                                                                    ("IF_Derail", ["PpoControlDeviceDerailmentStockCi"]),
                                                                    ("IF_Track", ["PpoTrackReceiverRi"]),
                                                                    ("IF_Coding", ["PpoCodeEnablingRelayALS",
                                                                                  "PpoTrackEncodingPoint"]),
                                                                    ("IF_Relay", ["PpoGeneralPurposeRelayInput",
                                                                                 "PpoGeneralPurposeRelayOutput"]),
                                                                    ("IF_PointService", ["PpoElectricHeatingRi"])])),
                                 ("TECHNOLOGY OBJECTS", OrderedDict([("TH_Zone", ["PpoControlAreaBorder"]),
                                                                     ("TH_Signal", ["PpoTrainSignal",
                                                                                   "PpoWarningSignal",
                                                                                   "PpoRepeatSignal",
                                                                                   "PpoShuntingSignal"]),
                                                                     ("TH_RoutePointer", ["PpoRoutePointer"]),
                                                                     ("TH_Track", ["PpoPointSection",
                                                                                  "PpoTrackSection",
                                                                                  "PpoTrackAnD",
                                                                                  "PpoLineEnd"]),
                                                                     ("TH_Point", ["PpoPoint"]),
                                                                     ("TH_AB", ["PpoAutomaticBlockingSystem"]),
                                                                     ("TH_PAB", ["PpoSemiAutomaticBlockingSystem"]),
                                                                     ("TH_CrossRoad", ["PpoTrackCrossroad",
                                                                                      "PpoRailCrossing"]),
                                                                     ("TH_Derail", ["PpoControlDeviceDerailmentStock"]),
                                                                     ("TH_Coding", ["PpoTrackUnit",
                                                                                   "PpoTrackEncodingPoint"]),
                                                                     ("TH_PointService", ["PpoElectricHeating"])])),
                                 ("ADJACENT POINT CLASSES", OrderedDict([("AP_ShSignal", ["PpoShuntingSignalWithTrackAnD"]),
                                                                         ("AP_TrackAND", ["PpoTrackAnDwithPoint"])])),
                                 ("ROUTE CLASSES", OrderedDict([("RT_TrainRoute", ["TrainRoute"]),
                                                                ("RT_ShuntingRoute", ["ShuntingRoute"])])),
                                 ("OPERATOR CLASSES", OrderedDict([("OP_Control", ["TrafficOperatorWorkset",
                                                                                   "StationOperatorWorkset",
                                                                                   "ControlArea"])])),
                                 ("TS CLASSES", OrderedDict([("TS_UsoBk", ["PpoCabinetUsoBk"]),
                                                             ("TS_Point", ["PpoInsulationResistanceMonitoring",
                                                                           "PpoPointMachinesCurrentMonitoring",
                                                                           "PpoPointsMonitoring"]),
                                                             ("TS_TS", ["PpoTelesignalization"]),
                                                             ("TS_Light", ["PpoLightModeRi",
                                                                           "PpoLightMode"]),
                                                             ("TS_Fire", ["PpoFireAndSecurityAlarm"]),
                                                             ("TS_DG", ["PpoDieselGenerator"])]))
                                 ])

TPL_TO_OBJ_ID = OrderedDict([('PpoPoint', "Str"),
                             ('PpoTrainSignal', "SvP"),
                             ('PpoShuntingSignal', "SvM"),
                             ('PpoPointSection', "SPU"),
                             ('PpoTrackSection', "SPU"),
                             ('PpoTrackAnD', "Put"),
                             ('PpoAutomaticBlockingSystem', "AdjAB"),
                             ('PpoSemiAutomaticBlockingSystem', "AdjPAB"),
                             ('PpoLineEnd', "Tpk"),
                             ('PpoControlAreaBorder', "GRU")])

DEFAULT_AUTO_ADD_IO = True
DEFAULT_SIGNAL_I_TYPE = "Ci"
DEFAULT_POINT_I_TYPE = "Ci"
DEFAULT_DERAIL_I_TYPE = "Ci"

ONE_LINE_HEIGHT = 28

SINGLE_ATTRIBUTE_PROPERTIES = "SINGLE_ATTRIBUTE_PROPERTIES"
NAMED_ATTRIBUTE_PROPERTIES = "NAMED_ATTRIBUTE_PROPERTIES"
ADDRESS = "ADDRESS"
PROPERTIES = "PROPERTIES"
INTERNAL_STRUCTURE = "INTERNAL_STRUCTURE"

LINE_EDIT_STYLESHEET = ("color: black;"
                        "background-color: white;"
                        "selection-color: yellow;"
                        "selection-background-color: blue;")

# print(len(CONFIG_FILE_JSON_NAMES))
# print(len(FILE_NAME_TO_CLASSES))

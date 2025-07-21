from dataclasses import dataclass


@dataclass
class SystemOS:
    system: str
    release: str
    version: str
    machine: str
    processor: str

@dataclass
class SystemCPU:
    physical_cores: int
    logical_cores: int
    max_frequency_mhz: int
    usage_pct: float = 0.0

@dataclass
class SystemMemory:
    total_gib: float
    used_gib: float = 0.0

@dataclass
class SystemNetwork:
    hostname: str
    fqdn: str
    local_ip: str
    public_ip: str
    interfaces: dict[str, list[str]]  # if_name: list of ip’s

@dataclass
class SystemDisk:
    device: str
    mountpoint: str
    fstype: str
    total_gib: float
    used_gib: float = 0.0

class EventLevel:
    INFO = "info"
    WARNING = "warn"
    CRITICAL = "crit"

class EventType:
    ONLINE = "online"
    OFFLINE = "offline"
    MISC = "misc"

@dataclass
class Event:
    level: EventLevel
    type: EventType
    timestamp: str
    description: str = ""

class SystemType:
    SERVER = "server"
    DESKTOP = "desktop"
    MINI_DESKTOP = "mini_desktop"
    LAPTOP = "laptop"
    MOBILE = "mobile"

@dataclass
class System:
    id: str
    name: str
    type: SystemType

    os: SystemOS = None
    cpu: SystemCPU = None
    memory: SystemMemory = None
    network: SystemNetwork = None
    disks: list[SystemDisk] = None
    events: list[Event] = None
    group: str = ""

class SiteType:
    HOUSE = "house"
    DATACENTER = "datacenter"
    CLOUD = "cloud"

@dataclass
class Site:
    name: str
    type: SiteType
    geoname: str
    systems: list[System]

@dataclass
class Provider:
    name: str
    sites: list[Site]
    url: str = ""


model_registry = {
    "SystemOS": SystemOS,
    "SystemCPU": SystemCPU,
    "SystemMemory": SystemMemory,
    "SystemNetwork": SystemNetwork,
    "SystemDisk": SystemDisk,
    "Event": Event,
    "System": System,
    "Site": Site,
    "Provider": Provider,
}
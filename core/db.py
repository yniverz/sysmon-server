import os
import json
from models import Provider, Site, System
from util import DataclassJSONDecoder, DataclassJSONEncoder


class SystemDB:
    def __init__(self, structure_path: str = "structure.json", data_path: str = "data.json"):
        self.structure_path = structure_path
        self.data_path = data_path
        self.providers: list[Provider] = []

        self.load_from_file()

    def create_structure(self):
        self.providers = []
        if not os.path.exists(self.structure_path):
            print(f"Structure file {self.structure_path} does not exist.")
        else:
            with open(self.structure_path, 'r') as f:
                structure = json.load(f)
                providers_data = structure.get("providers", [])
                for provider_data in providers_data:
                    sites_data = provider_data.get("sites", [])
                    sites = []
                    for site_data in sites_data:
                        systems_data = site_data.get("systems", [])
                        systems = [System(**system) for system in systems_data]

                        sites.append(Site(
                            name=site_data["name"],
                            type=site_data["type"],
                            geoname=site_data.get("geoname", ""),
                            systems=systems
                        ))

                    self.providers.append(Provider(
                        name=provider_data["name"],
                        sites=sites,
                        url=provider_data.get("url", "")
                    ))

            # create a hash of the template file
            file_hash = hash(json.dumps(structure, sort_keys=True))
            with open("template_hash.txt", 'w') as f:
                f.write(str(file_hash))

    def generate_structure_file(self):
        structure = {
            "providers": []
        }

        for provider in self.providers:
            provider_data = {
                "name": provider.name,
                "sites": []
            }

            for site in provider.sites:
                site_data = {
                    "name": site.name,
                    "type": site.type,
                    "systems": []
                }

                for system in site.systems:
                    system_data = {
                        "id": system.id,
                        "name": system.name,
                        "type": system.type
                    }
                    if system.group:
                        system_data["group"] = system.group

                    site_data["systems"].append(system_data)

                provider_data["sites"].append(site_data)

            structure["providers"].append(provider_data)

        with open(self.structure_path, "w", encoding="utf-8") as f:
            import json
            json.dump(structure, f, indent=4, ensure_ascii=False)


    def load_from_file(self):
        if not os.path.exists(self.data_path):
            self.create_structure()
            return

        with open(self.data_path, 'r') as f:
            self.providers = json.load(f, cls=DataclassJSONDecoder)


    def save_to_file(self):
        sorted_providers = sorted(self.providers, key=lambda p: p.name.lower())
        for provider in sorted_providers:
            provider.sites = sorted(provider.sites, key=lambda s: s.name.lower())
            for site in provider.sites:
                site.systems = sorted(site.systems, key=lambda sys: sys.name.lower())

        with open(self.data_path, 'w') as f:
            json.dump(sorted_providers, f, cls=DataclassJSONEncoder)

        self.generate_structure_file()


    def get_system(self, system_id: str) -> System | None:
        for provider in self.providers:
            for site in provider.sites:
                for system in site.systems:
                    if system.id == system_id:
                        return system
        return None
    
    def update_system(self, system_id: str, **kwargs):
        system = self.get_system(system_id)
        if not system:
            raise ValueError(f"System with ID {system_id} not found.")

        for key, value in kwargs.items():
            if hasattr(system, key):
                setattr(system, key, value)
            else:
                raise ValueError(f"Invalid attribute {key} for System.")

        self.save_to_file()

    def add_provider(self, provider: Provider):
        self.providers.append(provider)

        self.save_to_file()

    def add_site(self, provider_name: str, site: Site):
        for provider in self.providers:
            if provider.name == provider_name:
                provider.sites.append(site)
                self.save_to_file()
                return site
        raise ValueError(f"Provider {provider_name} not found.")
    
    def add_system(self, site_name: str, system: System):
        if self.get_system(system.id):
            raise ValueError(f"System with ID {system.id} already exists.")

        for provider in self.providers:
            for site in provider.sites:
                if site.name == site_name:
                    site.systems.append(system)
                    self.save_to_file()
                    return system
        raise ValueError(f"Site {site_name} not found.")
    
    def remove_system(self, system_id: str):
        for provider in self.providers:
            for site in provider.sites:
                for system in site.systems:
                    if system.id == system_id:
                        site.systems.remove(system)
                        self.save_to_file()
                        return system
        raise ValueError(f"System with ID {system_id} not found.")
    
    def remove_site(self, provider_name: str, site_name: str):
        for provider in self.providers:
            if provider.name == provider_name:
                for site in provider.sites:
                    if site.name == site_name:
                        provider.sites.remove(site)
                        self.save_to_file()
                        return site
        raise ValueError(f"Site {site_name} not found in provider {provider_name}.")
    
    def remove_provider(self, provider_name: str):
        for provider in self.providers:
            if provider.name == provider_name:
                self.providers.remove(provider)
                self.save_to_file()
                return provider
        raise ValueError(f"Provider {provider_name} not found.")
    
    def edit_system(self, system_id: str, **kwargs):
        system = self.get_system(system_id)
        if not system:
            raise ValueError(f"System with ID {system_id} not found.")

        for key, value in kwargs.items():
            if hasattr(system, key):
                setattr(system, key, value)
            else:
                raise ValueError(f"Invalid attribute {key} for System.")

        self.save_to_file()

    def edit_system_id(self, old_id: str, new_id: str):
        system = self.get_system(old_id)
        if not system:
            raise ValueError(f"System with ID {old_id} not found.")
        if not new_id:
            raise ValueError("New ID is required.")
        if self.get_system(new_id):
            raise ValueError(f"System with ID {new_id} already exists.")
        system.id = new_id
        self.save_to_file()

    def edit_site(self, provider_name: str, site_name: str, **kwargs):
        for provider in self.providers:
            if provider.name == provider_name:
                for site in provider.sites:
                    if site.name == site_name:
                        for key, value in kwargs.items():
                            if hasattr(site, key):
                                setattr(site, key, value)
                            else:
                                raise ValueError(f"Invalid attribute {key} for Site.")
                        self.save_to_file()
                        return site
        raise ValueError(f"Site {site_name} not found in provider {provider_name}.")
    
    def edit_provider(self, provider_name: str, **kwargs):
        for provider in self.providers:
            if provider.name == provider_name:
                for key, value in kwargs.items():
                    if hasattr(provider, key):
                        setattr(provider, key, value)
                    else:
                        raise ValueError(f"Invalid attribute {key} for Provider.")
                self.save_to_file()
                return provider
        raise ValueError(f"Provider {provider_name} not found.")
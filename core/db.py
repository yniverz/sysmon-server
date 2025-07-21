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

    def load_from_file(self):
        if not os.path.exists(self.data_path):
            self.create_structure()
            return
        
        if not os.path.exists("template_hash.txt"):
            self.create_structure()
            return
    
        with open("template_hash.txt", 'r') as f:
            template_hash = f.read().strip()
        with open(self.structure_path, 'r') as f:
            structure = json.load(f)
        current_hash = hash(json.dumps(structure, sort_keys=True))
        if str(current_hash) != template_hash:
            print("Template has changed, recreating structure.")
            self.create_structure()
            return

        with open(self.data_path, 'r') as f:
            self.providers = json.load(f, cls=DataclassJSONDecoder)


    def save_to_file(self):
        print(f"Saving {len(self.providers)} providers to {self.data_path}")
        with open(self.data_path, 'w') as f:
            json.dump(self.providers, f, cls=DataclassJSONEncoder)


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
        for provider in self.providers:
            for site in provider.sites:
                if site.name == site_name:
                    site.systems.append(system)
                    self.save_to_file()
                    return system
        raise ValueError(f"Site {site_name} not found.")
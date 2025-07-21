import os
from flask import json
from models import Provider, Site, System
from util import DataclassJSONDecoder, DataclassJSONEncoder


class SystemDB:
    def __init__(self, file_path: str = "structure.json"):
        self.file_path = file_path
        self.providers: list[Provider] = []

        self.load_from_file()

    def load_from_file(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, 'r') as f:
            self.providers = json.load(f, cls=DataclassJSONDecoder)

    def save_to_file(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.providers, f, cls=DataclassJSONEncoder)



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
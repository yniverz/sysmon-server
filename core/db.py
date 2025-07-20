import os
from flask import json
from models import Provider, Site, System
from util import DataclassJSONDecoder, DataclassJSONEncoder


class SystemDB:
    def __init__(self, file_path: str = "structure.json"):
        self.providers: list[Provider] = []

        self.load_from_file(file_path)

    def load_from_file(self, file_path: str):
        if not os.path.exists(file_path):
            return
        
        with open(file_path, 'r') as f:
            self.providers = json.load(f, cls=DataclassJSONDecoder)

    def save_to_file(self, file_path: str):
        with open(file_path, 'w') as f:
            json.dump(self.providers, f, cls=DataclassJSONEncoder)



    def add_provider(self, provider: Provider):
        self.providers.append(provider)

    def add_site(self, provider_name: str, site: Site):
        for provider in self.providers:
            if provider.name == provider_name:
                provider.sites.append(site)
                return site
        raise ValueError(f"Provider {provider_name} not found.")
    
    def add_system(self, site_name: str, system: System):
        for provider in self.providers:
            for site in provider.sites:
                if site.name == site_name:
                    site.systems.append(system)
                    return system
        raise ValueError(f"Site {site_name} not found.")
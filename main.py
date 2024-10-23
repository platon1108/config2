import requests
import xml.etree.ElementTree as ET
import graphviz
import os
import csv

class Package:
    def __init__(self, group_id, artifact_id, version, graph):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.name = f"{group_id}.{artifact_id}/{version}"
        self.dependencies = []


def find_release_version(url):
    try:
        response = requests.get(url)
    except Exception:
        return ""
    if response.status_code != 200:
        return ""
    
    root = ET.fromstring(response.text)
    namespace = '{' + root.tag.split('}')[0].strip('{') + '}'
    try:
        version = root.find('versioning').find('release')
    except Exception as e:
        raise
        return ""
    return version.text


def parse_dependencies(data, package, currdepth):
    group_id = package.group_id
    artifact_id = package.artifact_id
    version = package.version
    
    print(f"[INF] Current package: {group_id}.{artifact_id}")
    if currdepth >= data["maxdepth"]:
        print(f"[INF] Max depth occured for package {group_id}.{artifact_id}")
        return None
    
    group_path = group_id.replace('.', '/')
    pom_url = f"{data['repo_url']}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
    try:
        response = requests.get(pom_url)
    except Exception:
        print(f"[ERR] Connection to {pom_url} is failed")
        return None
    if response.status_code != 200:
        print(f"[ERR] HTTP error {response.status_code} occured while conneting to {pom_url}")
        return None
    
    root = ET.fromstring(response.text)
    namespace = '{' + root.tag.split('}')[0].strip('{') + '}'
    root = root.find(namespace + 'dependencies')
    if root is None:
        print(f"[INF] No dependencies found for package {group_id}.{artifact_id}")
        return None
     
    for dependency in root.findall(namespace + 'dependency'):
        try:
            curr_group_id = dependency.find(namespace + 'groupId').text
            curr_artifact_id = dependency.find(namespace + 'artifactId').text
        except AttributeError:
            print(f"[ERR] Incorrect package found in dependecies of package {group_id}.{artifact_id}")
            continue
        try:
            curr_version = dependency.find(namespace + 'version').text
        except AttributeError:
            curr_group_path = curr_group_id.replace('.', '/')
            print(f"[INF] No version found for package {curr_group_id}.{curr_artifact_id}. Trying to find release version")
            curr_version = find_release_version(f"{data['repo_url']}/{curr_group_path}/{curr_artifact_id}/maven-metadata.xml")
            if not curr_version:
                print(f"[ERR] Attemp to find release version of package {curr_group_id}.{curr_artifact_id} is failed")
                continue
            else:
                print(f"[INF] Release version of package {curr_group_id}.{curr_artifact_id} is found: {curr_version}")
    
        if f"{curr_group_id}/{curr_artifact_id}" not in data["packages"]:
            curr_package = Package(curr_group_id, curr_artifact_id, curr_version, data["graph"])
            data['packages'][f"{curr_group_id}/{curr_artifact_id}"] = curr_package
            parse_dependencies(data, curr_package, currdepth + 1)  
        else:
            print(f"[INF] Package {curr_group_id}/{curr_artifact_id} has already exists")
            curr_package = data['packages'][f"{curr_group_id}/{curr_artifact_id}"]
        data["graph"].edge(package.name, curr_package.name)
        package.dependencies.append(curr_package)
    return None


def main():
    with open('config.csv', 'r') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=";")
        for row in spamreader:
            programpath, name, URL, pngfilepath, maxdepth = row
    
    pngfilepath = pngfilepath.replace('.png', '', 1)
    os.environ["PATH"] += os.pathsep + programpath
    if '/' in name:
        group, version = name.split('/')
        *group, artifact_id = group.split('.')
        group_id = '.'.join(group)
    else:
        *group, artifact_id = name.split('.')
        group_id = '.'.join(group)
        print(f"[INF] No version provided for start package {group_id}.{artifact_id}. Trying to find release version")
        group_path = group_id.replace('.', '/')
        version = find_release_version(f"{URL}/{group_path}/{artifact_id}/maven-metadata.xml")
        if not version:
            print(f"[ERR] Attemp to find release version of package {group_id}.{artifact_id} is failed")
            return
        else:
            print(f"[INF] Release version of package {group_id}.{artifact_id} is found: {version}")

    graph = graphviz.Digraph(format="png")
    graph.attr(layout="neato")
    graph.attr(overlap="false")
    data = {"repo_url": URL, "maxdepth": int(maxdepth), "graph": graph}
    package = Package(group_id, artifact_id, version, data["graph"])
    data["packages"] = {f"{group_id}/{artifact_id}": package}
    parse_dependencies(data, package, 0)
    data["graph"].render(pngfilepath)
    print(f"[INF] PNG file created succesfully ({pngfilepath})")
    os.remove(pngfilepath)
    
main()

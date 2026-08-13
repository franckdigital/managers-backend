import os
import zipfile
from xml.etree import ElementTree as ET

from django.conf import settings


def import_scorm_package(lesson):
    """Extracts the uploaded zip and parses imsmanifest.xml (SCORM Content Aggregation
    Model: organizations/organization/item -> resources/resource/@href) to resolve the
    real launch file and detect 1.2 vs 2004 — replacing a manually-typed launch URL."""

    if not lesson.scorm_package:
        raise ValueError('Aucun paquet SCORM associé à cette leçon.')

    extract_dir_rel = os.path.join('courses', 'scorm_extracted', str(lesson.id))
    extract_dir_abs = os.path.join(settings.MEDIA_ROOT, extract_dir_rel)
    os.makedirs(extract_dir_abs, exist_ok=True)

    with zipfile.ZipFile(lesson.scorm_package.path) as archive:
        _safe_extract(archive, extract_dir_abs)

    manifest_path = os.path.join(extract_dir_abs, 'imsmanifest.xml')
    if not os.path.exists(manifest_path):
        raise ValueError("Paquet invalide : imsmanifest.xml introuvable à la racine de l'archive.")

    identifier, version, launch_href = _parse_manifest(manifest_path)

    extract_dir_url = extract_dir_rel.replace('\\', '/')
    lesson.scorm_extracted_path = extract_dir_url
    lesson.scorm_identifier = identifier
    lesson.scorm_version = version
    lesson.scorm_launch_url = f"{settings.MEDIA_URL.rstrip('/')}/{extract_dir_url}/{launch_href}".replace('\\', '/')
    lesson.save(update_fields=['scorm_extracted_path', 'scorm_identifier', 'scorm_version', 'scorm_launch_url'])
    return lesson


def _safe_extract(archive, target_dir):
    target_dir = os.path.realpath(target_dir)
    for member in archive.infolist():
        member_path = os.path.realpath(os.path.join(target_dir, member.filename))
        if not (member_path == target_dir or member_path.startswith(target_dir + os.sep)):
            raise ValueError("Paquet SCORM invalide (chemin suspect dans l'archive).")
    archive.extractall(target_dir)


def _parse_manifest(manifest_path):
    root = ET.parse(manifest_path).getroot()
    ns_uri = root.tag.split('}')[0].strip('{') if root.tag.startswith('{') else ''
    ns = {'ims': ns_uri} if ns_uri else {}

    def find(tag, parent):
        return parent.find(f'ims:{tag}', ns) if ns else parent.find(tag)

    def findall(tag, parent):
        return parent.findall(f'ims:{tag}', ns) if ns else parent.findall(tag)

    identifier = root.get('identifier', '')

    schema_version_text = ''
    metadata_el = find('metadata', root)
    if metadata_el is not None:
        schemaversion_el = find('schemaversion', metadata_el)
        if schemaversion_el is not None and schemaversion_el.text:
            schema_version_text = schemaversion_el.text
    version = '2004' if '2004' in schema_version_text else '1.2'

    organizations_el = find('organizations', root)
    if organizations_el is None:
        raise ValueError('Manifeste SCORM invalide : balise <organizations> manquante.')

    default_org_id = organizations_el.get('default')
    orgs = findall('organization', organizations_el)
    if not orgs:
        raise ValueError('Manifeste SCORM invalide : aucune <organization> trouvée.')
    organization = next((o for o in orgs if o.get('identifier') == default_org_id), orgs[0])

    first_item = find('item', organization)
    if first_item is None:
        raise ValueError('Manifeste SCORM invalide : aucun <item> de lancement trouvé.')

    resource_ref = first_item.get('identifierref')
    resources_el = find('resources', root)
    resource = None
    if resources_el is not None and resource_ref:
        resource = next((r for r in findall('resource', resources_el) if r.get('identifier') == resource_ref), None)

    if resource is None or not resource.get('href'):
        raise ValueError('Manifeste SCORM invalide : ressource de lancement introuvable ou sans href.')

    return identifier, version, resource.get('href')

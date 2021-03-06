#!/usr/bin/env python3

import argparse
import json
import logging
import urllib.request
import sys
import os.path

VERSION = '1.0'

def open_file_or_url(url):
    """
    open file or URL and return closeable fh
    """
    if url.startswith("http"):
        logging.info(f"  Loading resource from URL {url}")
        return urllib.request.urlopen(url)

    else:
        logging.info(f"  Loading resource from file {url}")
        return open(url, 'r')


def save_json(data, filename, opts):
    """
    Save JSON data in file.
    """
    fn = filename
    dir = opts.get('output_directory', None)
    if dir:
        fn = dir + '/' + fn
        
    logging.info(f"  Writing file {fn}")
    if os.path.isfile(fn):
        logging.warning(f"File {fn} will be overwritten.")
        
    with open(fn, 'w') as file:
        json.dump(data, file)


def get_string(val):
    """
    returns val as string.
    
    returns value[0] if it is a list of one element, 
    returns repr(value) otherwise.
    """
    if isinstance(val, str):
        return val
    elif isinstance(val, list) and len(val) == 1:
        return val[0]
    else:
        return repr(val)


def put_add(item, key, val, single_item_list=True):
    """
    puts val in dict item at key, adds val to list if item already has value
    """
    oldval = item.get(key, None)
    if oldval is None:
        if single_item_list:
            item[key] = [val]
        else:
            item[key] = val
    elif isinstance(oldval, list):
        oldval.append(val)
    else:
        item[key] = [oldval, val]


def parse_annotation(anno):
    """
    parse V2 or V3 annotation
    """
    if anno.get('type', None) == 'Annotation':
        return parse_annotation_v3(anno)
    
    elif anno.get('@type', None) == 'oa:Annotation':
        return parse_annotation_v2(anno)
    
    raise ValueError("Annotation type not found!")


def parse_annotation_v2(anno):
    """
    Parse anno as IIIF V2 annotation
    """
    anno_id = anno.get('@id', None)
    logging.debug(f"Annotation id: {anno_id}")
    if  not anno_id:
        raise ValueError("Annotation has no id")

    anno_target = anno.get('on', None)
    if  not anno_target:
        raise ValueError(f"Annotation {anno_id} has no target")
    
    if isinstance(anno_target, str):
        # target is URI, split off fragment selector
        target_uri, _, frag = anno_target.partition('#')
        
    elif isinstance(anno_target, dict):
        if 'id' in anno_target:
            target_uri = anno_target['id']
            
        elif 'full' in anno_target:
            target_uri = anno_target['full']
        
        else:
            raise ValueError(f"Annotation {anno_id} target has no id or full")

    else:
        raise ValueError(f"Annotation {anno_id} target is not str or dict")
    
    logging.debug(f"Annotation target URI: {target_uri}")
    
    if 'motivation' in anno:
        motivation = get_string(anno.get('motivation', None))
    else:
        motivation = None

    annotation_info = {
        'version': 2,
        'id': anno_id,
        'target': target_uri,
        'motivation': motivation,
        'annotation': anno
    }
    return annotation_info


def parse_annotation_v3(anno):
    """
    Parse anno as IIIF V3 annotation
    """
    anno_id = anno.get('id', None)
    logging.debug(f"Annotation id: {anno_id}")
    if  not anno_id:
        raise ValueError("Annotation has no id")

    anno_target = anno.get('target', None)
    if  not anno_target:
        raise ValueError(f"Annotation {anno_id} has no target")
    
    if isinstance(anno_target, str):
        # target is URI, split off fragment selector
        target_uri, _, frag = anno_target.partition('#')
        
    elif isinstance(anno_target, dict):
        if 'id' in anno_target:
            target_uri = anno_target['id']
            
        elif 'source' in anno_target:
            target_uri = anno_target['source']
        
        else:
            raise ValueError(f"Annotation {anno_id} target has no id or source")

    else:
        raise ValueError(f"Annotation {anno_id} target is not str or dict")
    
    logging.debug(f"Annotation target URI: {target_uri}")
    
    if 'motivation' in anno:
        motivation = get_string(anno.get('motivation', None))
    else:
        motivation = None

    annotation_info = {
        'version': 3,
        'id': anno_id,
        'target': target_uri,
        'motivation': motivation,
        'annotation': anno
    }
    return annotation_info


def parse_annotationlist_v2(annolist, annotation_info):
    """
    Parse annolist as V2 sc:AnnotationList for annotations.
    
    Stores results in annotation_info.
    Loads external annotationlists via HTTP.
    """
    if annotation_info is None:
        annotation_info = {
            'annotations': [],
            'by_target': dict(),
            'motivations': set()
        }
        
    annotations = annotation_info['annotations']
    targets = annotation_info['by_target']
    motivations = annotation_info['motivations']
    
    annolist_id = annolist.get('@id', None)
    logging.debug(f"AnnotationList id: {annolist_id}")
    if not annolist_id:
        raise ValueError("AnnotationList has no id")
    
    if annolist.get('@type', None) != 'sc:AnnotationList':
        raise ValueError(f"AnnotationList {annolist_id} not of type sc:AnnotationList")

    if not 'resources' in annolist:
        # external AnnotationList
        with open_file_or_url(annolist_id) as file:
            ext_annolist = json.load(file)
            return parse_annotationlist_v2(ext_annolist, annotation_info)
        
    annolist_items = annolist.get('resources', None)
    if  annolist_items is None or not isinstance(annolist_items, list):
        raise ValueError(f"AnnotationList has no resources!")
    
    for anno in annolist_items:
        anno_info = parse_annotation(anno)
        annotations.append(anno_info)
        put_add(targets, anno_info['target'], anno_info)
        motivations.add(anno_info['motivation'])

    return annotation_info


def parse_annotationlist_v3(annolist, annotation_info):
    """
    Parse annolist as V3 AnnotationPage for annotations.
    
    loads external annotationpage via HTTP.
    """
    if annotation_info is None:
        annotation_info = {
            'annotations': [],
            'by_target': dict(),
            'motivations': set()
        }
        
    annotations = annotation_info['annotations']
    targets = annotation_info['by_target']
    motivations = annotation_info['motivations']

    annolist_id = annolist.get('id', None)
    logging.debug(f"AnnotationPage id: {annolist_id}")
    if  not annolist_id:
        raise ValueError("AnnotationPage has no id")
    
    if annolist.get('type', None) != 'AnnotationPage':
        raise ValueError(f"AnnotationPage {annolist_id} not of type AnnotationPage")

    if not 'items' in annolist:
        # external AnnotationPage
        with open_file_or_url(annolist_id) as file:
            ext_annolist = json.load(file)
            return parse_annotationlist_v3(ext_annolist, annotation_info)

    annolist_items = annolist.get('items', None)
    if  annolist_items is None or not isinstance(annolist_items, list):
        raise ValueError(f"AnnotationPage has no items!")

    for anno in annolist_items:
        anno_info = parse_annotation(anno)
        annotations.append(anno_info)
        put_add(targets, anno_info['target'], anno_info)
        motivations.add(anno_info['motivation'])

    return annotation_info


def create_annotationlist_v2(manifest_info, annolist_id, annotation_infos, add_context=False):
    """
    Return V2 AnnotationList structure from annotation_infos
    """
    annolist = {
        '@type': 'sc:AnnotationList',
        '@id': annolist_id,
        'within': manifest_info['id']
    }
    if add_context:
        annolist['@context'] = 'http://iiif.io/api/presentation/2/context.json'
        
    annolist['resources'] = [ai['annotation'] for ai in annotation_infos]
    return annolist


def create_annotationlist_v3(manifest_info, annolist_id, annotation_infos, add_context=False):
    """
    Return V3 AnnotationPage structure from annotation_infos
    """
    annolist = {
        'type': 'AnnotationPage',
        'id': annolist_id,
        'partOf': manifest_info['id']
    }
    if add_context:
        annolist['@context'] = 'http://iiif.io/api/presentation/3/context.json'

    annolist['items'] = [ai['annotation'] for ai in annotation_infos]
    return annolist


def parse_manifest(manif, manifest_info, opts):
    """
    parse V2 or V3 manifest for annotations
    """
    if manifest_info is None:
        annotation_info = {
            'annotations': [],
            'by_target': dict(),
            'motivations': set()
        }
        manifest_info = {
            'annotations': annotation_info,
            'manifest': manif
        }
    
    ctx = manif.get('@context', None)
    if ctx == 'http://iiif.io/api/presentation/3/context.json':
        return parse_manifest_v3(manif, manifest_info, opts)
    
    elif ctx == 'http://iiif.io/api/presentation/2/context.json':
        return parse_manifest_v2(manif, manifest_info, opts)
    
    raise ValueError("No applicable JSON-LD context found! Manifest is not IIIF V2 or V3 manifest!")


def parse_manifest_v2(manif, manifest_info, opts):
    """
    Parse IIIF V2 manifest for annotations.
    
    Reads into manifest_info if opts['mode'] == 'read'.
    Inserts annotations from manifest_info into manif if  opts['mode'] == 'insert'.
    """
    annotation_info = manifest_info['annotations']
    canvas_ids = set()
    annolist_idx = 0
    
    if manif.get('@type', None) != 'sc:Manifest':
        raise ValueError("Manifest not of type Manifest")
    
    manif_id = manif.get('@id', None)
    logging.debug(f"manifest id: {manif_id}")
    if  not manif_id:
        raise ValueError("Manifest has no id")
    
    manif_label = manif.get('label', None)
    logging.debug(f"manifest label: {manif_label}")
    if  not manif_label:
        raise ValueError("Manifest has no label")
    
    manif_sequences = manif.get('sequences', None)
    if  manif_sequences is None or not isinstance(manif_sequences, list) or len(manif_sequences) < 1:
        raise ValueError("Manifest has no sequences")
    
    logging.debug(f"manifest has {len(manif_sequences)} sequences.")

    for sequence in manif_sequences:
        if sequence.get('@type', None) != 'sc:Sequence':
            raise ValueError(f"Sequence not of type sc:Sequence")
        
        canvases = sequence.get('canvases', None)
        if not canvases or not isinstance(canvases, list) or len(canvases) < 1:
            raise ValueError("Sequence has no canvases")

        for canvas in canvases:
            canvas_id = canvas.get('@id', None)
            logging.debug(f"canvas id: {canvas_id}")
            if  not canvas_id:
                raise ValueError("Canvas has no id")
            
            if canvas.get('@type', None) != 'sc:Canvas':
                raise ValueError(f"Canvas {canvas_id} not of type sc:Canvas")
        
            canvas_label = canvas.get('label', None)
            logging.debug(f"canvas label: {canvas_label}")
            if  not canvas_label:
                raise ValueError(f"Canvas {canvas_id} has no label")
            
            canvas_images = canvas.get('images', None)
            if  canvas_images is None or not isinstance(canvas_images, list):
                raise ValueError(f"Canvas {canvas_id} has no images")

            canvas_annos = canvas.get('otherContent', None)
            if opts['mode'] == 'read':
                #
                # read mode: record canvas id and annotations
                #
                canvas_ids.add(canvas_id)
                if  canvas_annos is None or not isinstance(canvas_annos, list):
                    # no annotationpages
                    continue

                for annolist in canvas_annos:
                    parse_annotationlist_v2(annolist, annotation_info)
                    
            elif opts['mode'] == 'insert':
                #
                # insert mode
                #
                annotations = annotation_info['by_target'].get(canvas_id, None)
                if annotations is None:
                    continue
                
                annolist_idx += 1
                annolist_id, annolist_fn = create_annotationlist_id(manifest_info, canvas_id, annolist_idx, opts)
                if opts['reference_mode'] == 'inline':
                    logging.warning("Inline AnnotationLists are not allowed in the IIIF V2 presentation API!")
                    annolist = create_annotationlist_v2(manifest_info, annolist_id, annotations, add_context=False)
                    canvas['otherContent'] = [annolist]
                    
                else:
                    annolist = create_annotationlist_v2(manifest_info, annolist_id, annotations, add_context=True)
                    save_json(annolist, annolist_fn, opts)
                    canvas['otherContent'] = [{
                        '@id': annolist_id,
                        '@type': 'sc:AnnotationList'
                    }]
            
    if opts['mode'] == 'read':
        manifest_info['manifest_version'] = 2
        manifest_info['id'] = manif_id
        manifest_info['label'] = manif_label
        manifest_info['canvas_ids'] = canvas_ids
        
    elif opts['mode'] == 'insert':
        manif['@id'] = manifest_info['id']
        manifest_info['manifest'] = manif

    return manifest_info


def parse_manifest_v3(manif, manifest_info, opts):
    """
    parse IIIF V3 manifest for annotations
    """
    annotation_info = manifest_info['annotations']
    canvas_ids = set()
    annolist_idx = 0
    
    if manif.get('type', None) != 'Manifest':
        raise ValueError("Manifest not of type Manifest")
    
    manif_id = manif.get('id', None)
    logging.debug(f"manifest id: {manif_id}")
    if  not manif_id:
        raise ValueError("Manifest has no id")
    
    manif_label = manif.get('label', None)
    logging.debug(f"manifest label: {manif_label}")
    if  not manif_label:
        raise ValueError("Manifest has no label")
    
    manif_items = manif.get('items', None)
    if  manif_items is None or not isinstance(manif_items, list):
        raise ValueError("Manifest has no items")
    
    logging.debug(f"manifest has {len(manif_items)} items")

    for canvas in manif_items:
        canvas_id = canvas.get('id', None)
        logging.debug(f"canvas id: {canvas_id}")
        if  not canvas_id:
            raise ValueError("Canvas has no id")
        
        if canvas.get('type', None) != 'Canvas':
            raise ValueError(f"Canvas {canvas_id} not of type Canvas")
    
        canvas_label = canvas.get('label', None)
        logging.debug(f"canvas label: {canvas_label}")
        if  not canvas_label:
            raise ValueError(f"Canvas {canvas_id} has no label")
        
        canvas_items = canvas.get('items', None)
        if  canvas_items is None or not isinstance(canvas_items, list):
            raise ValueError(f"Canvas {canvas_id} has no items")
    
        canvas_ids.add(canvas_id)
        canvas_annos = canvas.get('annotations', None)
        if opts['mode'] == 'read':
            #
            # read mode: record canvas id and annotations
            #
            canvas_ids.add(canvas_id)
            if  canvas_annos is None or not isinstance(canvas_annos, list):
                # no annotationpages
                continue

            for annolist in canvas_annos:
                parse_annotationlist_v3(annolist, annotation_info)
                
        elif opts['mode'] == 'insert':
            #
            # insert mode
            #
            annotations = annotation_info['by_target'].get(canvas_id, None)
            if annotations is None:
                continue
            
            annolist_idx += 1
            annolist_id, annolist_fn = create_annotationlist_id(manifest_info, canvas_id, annolist_idx, opts)
            if opts['reference_mode'] == 'inline':
                annolist = create_annotationlist_v3(manifest_info, annolist_id, annotations, add_context=False)
                canvas['annotations'] = [annolist]
                
            else:
                annolist = create_annotationlist_v3(manifest_info, annolist_id, annotations, add_context=True)
                save_json(annolist, annolist_fn, opts)
                canvas['annotations'] = [{
                    'id': annolist_id,
                    'type': 'AnnotationPage'
                }]

    if opts['mode'] == 'read':
        manifest_info = {
            'manifest_version': 3,
            'id': manif_id,
            'label': manif_label,
            'canvas_ids': canvas_ids,
            'annotations': annotation_info,
            'manifest': manif
        }
        
    elif opts['mode'] == 'insert':
        manif['id'] = manifest_info['id']
        manifest_info['manifest'] = manif
        
    return manifest_info


def create_annotationlist_id(manifest_info, canvas_id, annolist_idx, opts):
    """
    Return (uri, filename) for annotation list
    """
    prefix = opts['url_prefix']
    if not prefix:
        # use manifest id as prefix
        prefix = manifest_info['id']

    scheme = opts['annolist_name_scheme']
    if scheme == 'canvas':
        # use last part of canvas id
        canvas_part = canvas_id.split('/')[-1]
        fn = canvas_part + '-annolist.json'
        uri = prefix + '/' + fn
    
    else:
        fn = f"annolist-{annolist_idx}.json"
        uri = prefix + '/' + fn
        
    return uri, fn


def create_manifest_id(manifest_info, opts):
    """
    Return (uri, filename) for manifest
    """
    prefix = opts['url_prefix']
    if not prefix:
        # use manifest id as prefix
        prefix = manifest_info['id']

    fn = opts['output_manifest']
    uri = prefix + '/' + fn
    return uri, fn
    

def action_check(args):
    """
    Action: check manifest_info and show information.
    """
    if args.input_manifest is None:
        sys.exit('ERROR: missing input_manifest parameter!')
        
    logging.info(f"Reading {args.input_manifest}")
    with open_file_or_url(args.input_manifest) as file:
        manif = json.load(file)
        manifest_info = parse_manifest(manif, None, {'mode': 'read'})
        annotation_info = manifest_info['annotations']
        logging.info(f"IIIF V{manifest_info['manifest_version']} manifest {manifest_info['id']}")
        logging.info(f"* label: '{manifest_info['label']}'")
        logging.info(f"* {len(manifest_info['canvas_ids'])} canvases")
        logging.info(f"* {len(annotation_info['annotations'])} annotations")
        if len(annotation_info['annotations']) > 0:
            logging.info(f"  * on {len(manifest_info['annotations']['by_target'])} canvases")
            logging.info(f"  * motivations: {manifest_info['annotations']['motivations']}")


def action_extract(args):
    """
    Action: extract annotations from manifest and save as AnnotationPage.
    """
    if args.input_manifest is None:
        sys.exit('ERROR: missing input_manifest parameter!')
        
    if args.output_file is None:
        sys.exit('ERROR: missing output_file parameter!')
        
    logging.info(f"Reading manifest {args.input_manifest}")
    with open_file_or_url(args.input_manifest) as file:
        manif = json.load(file)
        manifest_info = parse_manifest(manif, None, {'mode': 'read'})
        num_annos = len(manifest_info['annotations']['annotations'])
        logging.info(f"IIIF V{manifest_info['manifest_version']} manifest {manifest_info['id']} contains {num_annos} annotations.")

    opts = vars(args)
    annos = manifest_info['annotations']['annotations']
    annolist_id, _ = create_annotationlist_id(manifest_info, None, 1, opts)
    if manifest_info['manifest_version'] == 2:
        logging.info(f"Writing IIIF V2 annotation list {args.output_file}")
        annolist = create_annotationlist_v2(manifest_info, annolist_id, annos, add_context=True)
    else:
        logging.info(f"Writing IIIF V3 annotation page {args.output_file}")
        annolist = create_annotationlist_v3(manifest_info, annolist_id, annos, add_context=True)
        
    save_json(annolist, args.output_file, opts)


def action_insert(args):
    """
    Action: insert annotations from AnnotationPage and save new manifest and annotation files.
    """
    if args.input_manifest is None:
        sys.exit('ERROR: missing input_manifest parameter!')
        
    if args.input_file is None:
        sys.exit('ERROR: missing input_file parameter!')
        
    if args.output_manifest is None:
        sys.exit('ERROR: missing output_manifest parameter!')
        
    logging.info(f"Reading manifest {args.input_manifest}")
    with open_file_or_url(args.input_manifest) as file:
        manif = json.load(file)
        manifest_info = parse_manifest(manif, None, {'mode': 'read'})
        num_annos = len(manifest_info['annotations']['annotations'])
        logging.info(f"IIIF V{manifest_info['manifest_version']} manifest {manifest_info['id']} contains {num_annos} annotations.")

    logging.info(f"Reading annotation file {args.input_file}")
    with open_file_or_url(args.input_file) as file:
        annos = json.load(file)
        if manifest_info['manifest_version'] == 2:
            annotation_info = parse_annotationlist_v2(annos, None) 
        
        else:
            annotation_info = parse_annotationlist_v3(annos, None) 

    opts = vars(args)
    opts['mode'] = 'insert'
    manifest_id, manifest_file = create_manifest_id(manifest_info, opts)
    manifest_info['id'] = manifest_id
    manifest_info['annotations'] = annotation_info
    logging.info(f"Creating new manifest {manifest_id}")
    # re-parse manifest, adding annotations and writing annotationlists
    manifest_info = parse_manifest(manif, manifest_info, opts)
    # save manifest
    save_json(manifest_info['manifest'], manifest_file, opts)


##
## main
##
def main():
    argp = argparse.ArgumentParser(description='Manipulate annotations in IIIF manifests.')
    argp.add_argument('--version', action='version', version='%(prog)s '+VERSION)
    argp.add_argument('action', choices=['check', 'extract', 'insert'],
                      default='check',
                      help='Action: check=check and print information about annotations in manifest, '
                      + 'extract=extract annotations from manifest, '
                      + 'insert=insert annotations and create new manifest.')
    argp.add_argument('-i', '--input-manifest', dest='input_manifest',
                      help='Input manifest file or URL (JSON)')
    argp.add_argument('-if', '--input-file', dest='input_file',
                      help='Input AnnotationPage/List file (JSON)')
    argp.add_argument('-of', '--output-file', dest='output_file',
                      help='Output AnnotationPage/List file (JSON)')
    argp.add_argument('-od', '--output-directory', dest='output_directory',
                      help='Output directory for AnnotationPage/List files (JSON)')
    argp.add_argument('-om', '--output-manifest', dest='output_manifest',
                      help='Output manifest file (JSON)')
    argp.add_argument('--reference-mode', dest='reference_mode', choices=['inline', 'reference'],
                      default='reference', 
                      help='Mode of storing annotations in manifest.')
    argp.add_argument('--url-prefix', dest='url_prefix',
                      help='URL prefix for AnnotationPage/List references and manifest.')
    argp.add_argument('--annolist-name-scheme', dest='annolist_name_scheme',
                      choices=['canvas', 'sequence'], default='sequence', 
                      help='Naming scheme for generated AnnotationPage/List files.')

    argp.add_argument('-l', '--log', dest='loglevel', choices=['INFO', 'DEBUG', 'ERROR'], default='INFO', 
                      help='Log level.')
    args = argp.parse_args()
    
    # set up 
    logging.basicConfig(level=args.loglevel)

    # actions
    if args.action == 'check':
        action_check(args)
        
    elif args.action == 'extract':
        action_extract(args)

    elif args.action == 'insert':
        action_insert(args)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import urllib.request
import sys

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


def get_string(val):
    """
    returns val as string.
    
    returns value[0] if it is a list of one element, 
    returns repr(value) otherwise.
    """
    if isinstance(val, list) and len(val) == 1:
        return val[0]
    else:
        return repr(val)


def parse_annotationlist(annolist, annotations, annotation_motivations):
    """
    Parse annolist as sc:AnnotationList for annotations.
    
    loads external annotationlists via HTTP.
    """
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
            return parse_annotationlist(ext_annolist, annotations, annotation_motivations)
        
    annolist_items = annolist.get('resources', None)
    if  annolist_items is None or not isinstance(annolist_items, list):
        raise ValueError(f"AnnotationList has no resources!")
    
    for anno in annolist_items:
        anno_id = anno.get('@id', None)
        logging.debug(f"Annotation id: {anno_id}")
        if  not anno_id:
            raise ValueError(f"Annotation in page {annolist_id} has no id")
        
        if anno.get('@type', None) != 'oa:Annotation':
            raise ValueError(f"Annotation {anno_id} not of type oa:Annotation")

        annotations.append(anno)
        if 'motivation' in anno:
            annotation_motivations.add(get_string(anno['motivation']))


def parse_annotationpage(annopage, annotations, annotation_motivations):
    """
    Parse annopage as AnnotationPage for annotations.
    
    loads external annotationpage via HTTP.
    """
    annopage_id = annopage.get('id', None)
    logging.debug(f"AnnotationPage id: {annopage_id}")
    if  not annopage_id:
        raise ValueError("AnnotationPage has no id")
    
    if annopage.get('type', None) != 'AnnotationPage':
        raise ValueError(f"AnnotationPage {annopage_id} not of type AnnotationPage")

    if not 'items' in annopage:
        # external AnnotationPage
        with open_file_or_url(annopage_id) as file:
            ext_annopage = json.load(file)
            return parse_annotationpage(ext_annopage, annotations, annotation_motivations)

    annopage_items = annopage.get('items', None)
    if  annopage_items is None or not isinstance(annopage_items, list):
        raise ValueError(f"AnnotationPage has no items!")

    for anno in annopage_items:
        anno_id = anno.get('id', None)
        logging.debug(f"Annotation id: {anno_id}")
        if  not anno_id:
            raise ValueError(f"Annotation in page {annopage_id} has no id")
        
        if anno.get('type', None) != 'Annotation':
            raise ValueError(f"Annotation {anno_id} not of type Annotation")

        annotations.append(anno)
        if 'motivation' in anno:
            annotation_motivations.add(get_string(anno['motivation']))


def parse_manifest(manif):
    """
    parse V2 or V3 manifest for annotations
    """
    ctx = manif.get('@context', None)
    if ctx == 'http://iiif.io/api/presentation/3/context.json':
        return parse_manifest_v3(manif)
    
    elif ctx == 'http://iiif.io/api/presentation/2/context.json':
        return parse_manifest_v2(manif)
    
    raise ValueError("No applicable JSON-LD context found! Manifest is not IIIF V2 or V3 manifest!")


def parse_manifest_v2(manif):
    """
    parse IIIF V2 manifest for annotations
    """
    manifest = {}
    annotations = []
    annotation_motivations = set()
    
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
            if  canvas_annos is None or not isinstance(canvas_annos, list):
                # no annotationpages
                continue
        
            for annopage in canvas_annos:
                parse_annotationlist(annopage, annotations, annotation_motivations)
            
    logging.debug(f"found {len(annotations)} annotations.")
    manifest = {
        'manifest_version': 2,
        'id': manif_id,
        'label': manif_label,
        'annotations': annotations,
        'annotation_motivations': annotation_motivations
    }
    return manifest


def parse_manifest_v3(manif):
    """
    parse IIIF V3 manifest for annotations
    """
    manifest = {}
    annotations = []
    annotation_motivations = set()
    
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

    for item in manif_items:
        canvas_id = item.get('id', None)
        logging.debug(f"canvas id: {canvas_id}")
        if  not canvas_id:
            raise ValueError("Canvas has no id")
        
        if item.get('type', None) != 'Canvas':
            raise ValueError(f"Canvas {canvas_id} not of type Canvas")
    
        canvas_label = item.get('label', None)
        logging.debug(f"canvas label: {canvas_label}")
        if  not canvas_label:
            raise ValueError(f"Canvas {canvas_id} has no label")
        
        canvas_items = item.get('items', None)
        if  canvas_items is None or not isinstance(canvas_items, list):
            raise ValueError(f"Canvas {canvas_id} has no items")
    
        canvas_annos = item.get('annotations', None)
        if  canvas_annos is None or not isinstance(canvas_annos, list):
            # no annotationpages
            continue
    
        for annopage in canvas_annos:
            parse_annotationpage(annopage, annotations, annotation_motivations)
            
    logging.debug(f"found {len(annotations)} annotations.")
    manifest = {
        'manifest_version': 3,
        'id': manif_id,
        'label': manif_label,
        'items': manif_items,
        'annotations': annotations,
        'annotation_motivations': annotation_motivations
    }
    return manifest

def create_annotationpage(manifest_info):
    """
    Create V3 AnnotationPage structure from manifest info
    """
    annopage = {
        '@context': 'http://iiif.io/api/presentation/3/context.json',
        'type': 'AnnotationPage',
    }
    annopage['items'] = manifest_info['annotations']
    return annopage

def create_annotationlist(manifest_info):
    """
    Create V2 AnnotationList structure from manifest info
    """
    annopage = {
        '@context': 'http://iiif.io/api/presentation/2/context.json',
        '@type': 'sc:AnnotationList',
    }
    annopage['resources'] = manifest_info['annotations']
    return annopage

def action_check(args):
    """
    Action: check manifest_info and show information.
    """
    if args.input_manifest is None:
        sys.exit('ERROR: missing input_manifest parameter!')
        
    logging.info(f"Reading {args.input_manifest}")
    with open_file_or_url(args.input_manifest) as file:
        manif = json.load(file)
        manifest_info = parse_manifest(manif)
        num_annos = len(manifest_info['annotations'])
        logging.info(f"IIIF V{manifest_info['manifest_version']} manifest {manifest_info['id']} contains {num_annos} annotations.")
        if num_annos > 0:
            logging.info(f"  annotation motivations: {manifest_info['annotation_motivations']}")


def action_extract(args):
    """
    Action: extract annotations from manifest and save as AnnotationPage.
    """
    if args.input_manifest is None:
        sys.exit('ERROR: missing input_manifest parameter!')
        
    if args.output_annotation_file is None:
        sys.exit('ERROR: missing output_annotation_file parameter!')
        
    logging.info(f"Reading file {args.input_manifest}")
    with open_file_or_url(args.input_manifest) as file:
        manif = json.load(file)
        manifest_info = parse_manifest(manif)
        logging.info(f"IIIF V{manifest_info['manifest_version']} manifest {manifest_info['id']} contains {len(manifest_info['annotations'])} annotations.")

    with open(args.output_annotation_file, "w") as file:
        if manifest_info['manifest_version'] == 2:
            logging.info(f"Writing IIIF V2 annotation list {args.output_annotation_file}")
            annopage = create_annotationlist(manifest_info)
        else:
            logging.info(f"Writing IIIF V3 annotation page {args.output_annotation_file}")
            annopage = create_annotationpage(manifest_info)
            
        json.dump(annopage, file)

##
## main
##
def main():
    argp = argparse.ArgumentParser(description='Manipulate annotations in IIIF manifests.')
    argp.add_argument('--version', action='version', version='%(prog)s 1.0')
    argp.add_argument('action', choices=['check', 'extract'], 
                      default='check', 
                      help='Action: check=check and print information about annotations in manifest, '
                      + 'extract=extract annotations from manifest.')
    argp.add_argument('-f', '--input-manifest', dest='input_manifest',
                      help='Input manifest file or URL (JSON)')
    argp.add_argument('-o', '--output-annotation-file', dest='output_annotation_file',
                      help='Output AnnotationPage/List file (JSON)')

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


if __name__ == '__main__':
    main()

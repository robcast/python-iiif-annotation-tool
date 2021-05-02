#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging


def parse_manifest_v3(manif):
    """
    parse manifest for annotations
    """
    manifest = {}
    annotations = []
    annotation_motivations = set()
    
    if manif.get('@context', None) != 'http://iiif.io/api/presentation/3/context.json':
        logging.error(f"Manifest has no IIIF-V3 context: {manif['@context']}")
        return False
        
    if manif.get('type', None) != 'Manifest':
        logging.error("Manifest not of type Manifest")
        return False
    
    manif_id = manif.get('id', None)
    logging.debug(f"manifest id: {manif_id}")
    if  not manif_id:
        logging.error("Manifest has no id")
        return False
    
    manif_label = manif.get('label', None)
    logging.debug(f"manifest label: {manif_label}")
    if  not manif_label:
        logging.error("Manifest has no label")
        return False
    
    manif_items = manif.get('items', None)
    if  manif_items is None or not isinstance(manif_items, list):
        logging.error("Manifest has no items")
        return False
    
    logging.debug(f"manifest has {len(manif_items)} items")

    for item in manif_items:
        canvas_id = item.get('id', None)
        logging.debug(f"canvas id: {canvas_id}")
        if  not canvas_id:
            logging.error("Canvas has no id")
            return False
        
        if item.get('type', None) != 'Canvas':
            logging.error(f"Canvas {canvas_id} not of type Canvas")
            return False
    
        canvas_label = item.get('label', None)
        logging.debug(f"canvas label: {canvas_label}")
        if  not canvas_label:
            logging.error(f"Canvas {canvas_id} has no label")
            return False
        
        canvas_items = item.get('items', None)
        if  canvas_items is None or not isinstance(canvas_items, list):
            logging.error(f"Canvas {canvas_id} has no items")
            return False
    
        canvas_annos = item.get('annotations', None)
        if  canvas_annos is None or not isinstance(canvas_annos, list):
            # no annotationpages
            continue
    
        for annopage in canvas_annos:
            annopage_id = annopage.get('id', None)
            logging.debug(f"AnnotationPage id: {annopage_id}")
            if  not annopage_id:
                logging.error("AnnotationPage has no id")
                return False
            
            if annopage.get('type', None) != 'AnnotationPage':
                logging.error(f"AnnotationPage {annopage_id} not of type AnnotationPage")
                return False

            annopage_items = annopage.get('items', None)
            if  annopage_items is None or not isinstance(annopage_items, list):
                # no annotations
                continue
        
            for anno in annopage_items:
                anno_id = anno.get('id', None)
                logging.debug(f"Annotation id: {anno_id}")
                if  not anno_id:
                    logging.error(f"Annotation in page {annopage_id} has no id")
                    return False
                
                if anno.get('type', None) != 'Annotation':
                    logging.error(f"Annotation {anno_id} not of type Annotation")
                    return False

                annotations.append(anno)
                if 'motivation' in anno:
                    annotation_motivations.add(anno['motivation'])
            
    logging.debug(f"found {len(annotations)} annotations.")
    manifest = {
        'id': manif_id,
        'label': manif_label,
        'items': manif_items,
        'annotations': annotations,
        'annotation_motivations': annotation_motivations
    }
    return manifest

def create_annopage(manifest):
    """
    Create AnnotationPage structure from manifest info
    """
    annopage = {
        'type': 'AnnotationPage',
    }
    annopage['items'] = manifest['annotations']
    return annopage


def action_check(args):
    """
    Action: check manifest and show information.
    """
    if args.input_manifest is None:
        sys.exit('ERROR: missing input_manifest parameter!')
        
    logging.info(f"Reading file {args.input_manifest}")
    with open(args.input_manifest, "r") as file:
        manif = json.load(file)
        manifest = parse_manifest_v3(manif)
        num_annos = len(manifest['annotations'])
        logging.info(f"Manifest {manifest['id']} contains {num_annos} annotations.")
        if num_annos > 0:
            logging.info(f"  annotation motivations: {manifest['annotation_motivations']}")


def action_extract(args):
    """
    Action: extract annotations from manifest and save as AnnotationPage.
    """
    if args.input_manifest is None:
        sys.exit('ERROR: missing input_manifest parameter!')
        
    if args.output_annopage is None:
        sys.exit('ERROR: missing output_annopage parameter!')
        
    logging.info(f"Reading file {args.input_manifest}")
    with open(args.input_manifest, "r") as file:
        manif = json.load(file)
        manifest = parse_manifest_v3(manif)
        logging.info(f"Manifest {manifest['id']} contains {len(manifest['canvas_annotations'])} annotations.")

    logging.info(f"Writing file {args.output_annopage}")
    with open(args.output_annopage, "w") as file:
        annopage = create_annopage(manifest)
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
                      help='Input manifest file (JSON)')
    argp.add_argument('-o', '--output-annopage', dest='output_annopage',
                      help='Output AnnotationPage file (JSON)')

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

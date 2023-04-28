#!/usr/bin/env python3

import anytree

from . import lookup

help_url = 'https://github.com/htem/FANC_auto_recon/wiki/Neuron-annotations#neuron_information'
help_msg = 'See the annotation scheme described at ' + help_url

annotation_hierarchy = {
    'primary class': {
        'sensory neuron': {
            'chordotonal neuron': {},
            'bristle neuron': {},
            'hair plate neuron': {},
            'campaniform sensillum neuron': {},
            'descending neuron': {},
            'ascending neuron': {}},
        'central neuron': {
            'descending neuron': {},
            'ascending neuron': {},
            'VNC interneuron': {}},
        'motor neuron': {
            'T1 leg motor neuron': {},
            'T2 leg motor neuron': {},
            'T3 leg motor neuron': {},
            'neck motor neuron': {},
            'wing motor neuron': {},
            'haltere motor neuron': {},
            'abdominal motor neuron': {}},
        'efferent non-motor neuron': {
            'UM neuron': {
                'T1 leg UM neuron': {},
                'T2 leg UM neuron': {},
                'T3 leg UM neuron': {},
                'neck UM neuron': {},
                'wing UM neuron': {},
                'haltere UM neuron': {},
                'abdominal UM neuron': {}}}
    },
    'projection pattern': {
        'local': {},
        'intersegmental': {},
        'unilateral': {},
        'bilateral': {}
    },
    'neuron identity': {}
}


def _dict_to_anytree(dict):
    """
    Given a dictionary containing a hierarchy of strings, return a dictionary
    with each string as a key and the corresponding anytree.Node as the value.
    """
    def _build_tree(annotations: dict, parent: dict = None, nodes: dict = {}):
        for annotation in annotations.keys():
            node = anytree.Node(annotation, parent=parent)
            nodes[annotation] = nodes.get(annotation, []) + [node]
            _build_tree(annotations[annotation], parent=node, nodes=nodes)
        return nodes
    
    return _build_tree(dict)

annotation_tree = _dict_to_anytree(annotation_hierarchy)


def print_annotation_tree():
    """
    Print the annotation hierarchy
    """
    def print_one_tree(root: str):
        for prefix, _, node in anytree.RenderTree(annotation_tree[root][0]):
            print(f'{prefix}{node.name}')
    print_one_tree('primary class')
    print_one_tree('projection pattern')


def guess_class(annotation: 'str') -> 'str':
    """
    Given an annotation, return the annotation class to which it belongs.
    """
    try:
        annotation_nodes = annotation_tree[annotation]
    except:
        raise ValueError(f'Class of "{annotation}" could not be guessed. {help_msg}')

    if len(annotation_nodes) > 1:
        raise ValueError(f'Class of "{annotation}" could not be guessed'
                         f' because it has multiple possible classes. {help_msg}')


    return annotation_nodes[0].parent.name



def is_valid_pair(annotation_class: str, annotation: str, raise_errors=True) -> bool:
    """
    Determine whether `annotation` is a valid annotation for the given
    `annotation_class`, according to the rules described at
    https://github.com/htem/FANC_auto_recon/wiki/Neuron-annotations#neuron_information
    """
    if annotation_class == 'neuron identity':
        if annotation in annotation_tree:
            if raise_errors:
                raise ValueError(f'The term "{annotation}" is a class,'
                                 f' not an identity. {help_msg}')
            return False
        return True
    
    try:
        class_nodes = annotation_tree[annotation_class]
    except:
        if raise_errors:
            raise ValueError(f'Annotation class "{annotation_class}" not'
                             f' recognized. {help_msg}')
        else:
            return False
    try:
        annotation_nodes = annotation_tree[annotation]
    except:
        if raise_errors:
            raise ValueError(f'Annotation "{annotation}" not recognized.'
                             f' {help_msg}')
        else:
            return False

    for class_node in class_nodes:
        for annotation_node in annotation_nodes:
            if annotation_node in class_node.children:
                return True

    if raise_errors:
        parent_names = [node.parent.name
                        if node.parent is not None else '<no class>'
                        for node in annotation_nodes]
        if len(annotation_nodes) == 1:
            raise ValueError(f'Annotation "{annotation}" belongs to class'
                             f' "{parent_names[0]}" but you specified class'
                             f' "{annotation_class}". {help_msg}')
        else:
            raise ValueError(f'Annotation "{annotation}" belongs to classes'
                             f' {parent_names} but you specified class'
                             f' "{annotation_class}". {help_msg}')

    else:
        return False
    
    return True

def is_allowed_to_post(segid, annotation_class, annotation,
                       table_name='neuron_information',
                       raise_errors=True) -> bool:
    """
    Determine whether a particular segment is allowed to be annotated
    with the given annotation+annotation_class pair.

    In addition to checking `is_valid_pair(annotation_class, annotation)`,
    this function checks the following rules:
    1. The given annotation pair may not be posted if the segment already has
    any annotation pair with the same annotation_class. This prevents exact
    duplicates, and also prevents a class from having multiple subclasses. This
    rule is not enforced for a few classes that are allowed to have multiple
    subannotations:
      - 'neuron identity'
      - 'projection pattern'
    2. The given annotation pair may only be posted if its annotation_class is
    at the root of the annotation tree (e.g. 'primary class'), or if its
    annotation_class is already an annotation on the segment. This ensures
    that each annotation adds detail/subclass information onto an existing
    annotation, or onto the root of the annotation tree.

    Returns
    -------
    bool
    - True: This segment MAY be annotated with the
      annotation+annotation_class pair in the given CAVE table without
      violating any rules about redundancy or mutual exclusivity.
    - False: The proposed annotation+annotation_class MAY NOT be
      applied to the segment without violating a rule. If `raise_errors`
      is True, an exception with an informative error message will be
      raised instead of returning False.
    """
    if not is_valid_pair(annotation_class, annotation, raise_errors=raise_errors):
        return False

    existing_annos = lookup.get_annotations(segid, table_name=table_name,
                                            return_as='dataframe')
    # Rule 1
    multiple_subclasses_allowed = [
        'neuron identity', 'projection pattern', 'sensory neuron'
    ]
    if annotation_class in multiple_subclasses_allowed:
        # Check if any tag,tag2 pair is the same as annotation,annotation_class
        if not existing_annos.loc[
                (existing_annos.tag == annotation) &
                (existing_annos.tag2 == annotation_class)].empty:
            if raise_errors:
                raise ValueError(f'Segment {segid} already has this exact'
                                 ' annotation pair.')
            return False
        # Multiple subclasses are only allowed if they don't violate the
        # following mutual exclusivity rules. For example, a neuron can't be
        # annotated with both 'unilateral' and 'bilateral'.
        exclusivity_groups = [
            # Exclusivity groups within 'projection pattern':
            {'unilateral', 'bilateral'},
            {'local', 'intersegmental'},
            # Exclusivity groups within 'sensory_neuron':
            {'ascending neuron', 'descending neuron'},
            {'chordotonal neuron', 'bristle neuron', 'hair plate neuron', 'campaniform sensillum neuron'}
        ]
        for group in exclusivity_groups:
            if annotation in group:
                # Check if any annotation in this group already exists
                if not existing_annos.loc[existing_annos.tag.isin(group)].empty:
                    if raise_errors:
                        raise ValueError(f'Segment {segid} already has an'
                                         f' annotation in the group'
                                         f' {group}. {help_msg}')
                    return False
        return True
    elif not existing_annos.loc[existing_annos.tag2 == annotation_class].empty:
        if raise_errors:
            raise ValueError(f'Segment {segid} already has an annotation with'
                             f' class "{annotation_class}". {help_msg}')
        return False

    # Rule 2
    root_classes = list(annotation_hierarchy.keys())
    if (annotation_class not in root_classes and
            existing_annos.loc[existing_annos.tag == annotation_class].empty):
        if raise_errors:
            raise ValueError(f'Segment {segid} must be annotated with'
                             f' "{annotation_class}" before this term can be'
                             f' used as an annotation class. {help_msg}')
        return False

    return True

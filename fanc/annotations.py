#!/usr/bin/env python3
"""
This module specifies rules governing what annotations are allowed to be posted
to certain "managed" CAVE tables (where only pre-approved types of annotations
may be posted). These rules are typically used for centralized community tables
to which many users can post annotations, in order to maintain some consistency
in which annotations are posted to the table.
"""

import anytree

from . import lookup

help_url = 'https://fanc.community/Neuron-annotations#neuron_information'
help_msg = 'See the annotation scheme described at ' + help_url

default_table = 'neuron_information'


cell_info = {
    'primary class': {
        'sensory neuron': {
            'chordotonal neuron': {
                'club chordotonal neuron': {},
                'claw chordotonal neuron': {},
                'hook chordotonal neuron': {}},
            'bristle neuron': {},
            'hair plate neuron': {},
            'campaniform sensillum neuron': {}},
        'central neuron': {},
        'motor neuron': {
            'leg motor neuron': {
                'T1 leg motor neuron': {
                    'L1 bundle': {},
                    'L2 bundle': {},
                    'L3 bundle': {},
                    'L4 bundle': {},
                    'L5 bundle': {},
                    'A1 bundle': {},
                    'A2 bundle': {},
                    'A3 bundle': {},
                    'A4 bundle': {},
                    'A5 bundle': {},
                    'V1 bundle': {},
                    'V2 bundle': {},
                    'V3 bundle': {},
                    'V4 bundle': {},
                    'V5 bundle': {},
                    'V6 bundle': {},
                    'D1 bundle': {},
                    'D2 bundle': {}},
                'T2 leg motor neuron': {
                    'L1 bundle': {},
                    'L6 bundle': {},
                    'L7 bundle': {},
                    'L8 bundle': {},
                    'L9 bundle': {},
                    'L10 bundle': {},
                    'L11 bundle': {},
                    'L12 bundle': {},
                    'L13 bundle': {},
                    'A6 bundle': {},
                    'A7 bundle': {},
                    'PDMN bundle': {}},
                'T3 leg motor neuron': {
                    'A11 bundle': {},
                    'A12 bundle': {},
                    'L1 bundle': {},
                    'L14 bundle': {},
                    'L15 bundle': {},
                    'L16 bundle': {},
                    'L18 bundle': {},
                    'tbd bundle': {}}},
            'neck motor neuron': {
                'C1 bundle': {},
                'D bundle': {}},
            'wing motor neuron': {
                'A8 bundle': {},
                'A9 bundle': {},
                'A10 bundle': {},
                'ADMN1 bundle': {},
                'ADMN2 bundle': {},
                'ADMN3 bundle': {},
                'PDMN1 bundle': {},
                'PDMN2 bundle': {}},
            'haltere motor neuron': {
                'HN bundle': {},
                'T3 H1 bundle': {},
                'T3 H2 bundle': {},
                'T3 H3 bundle': {}},
            'abdominal motor neuron': {}},
        'efferent non-motor neuron': {
            'UM neuron': {
                'T1 leg UM neuron': {},
                'T2 leg UM neuron': {},
                'T3 leg UM neuron': {},
                'neck UM neuron': {},
                'wing UM neuron': {},
                'haltere UM neuron': {},
                'abdominal UM neuron': {}}},
        'glia': {
            'trachea': {}}},
    'soma side': {
        'left soma': {},
        'right soma': {},
        'midline soma': {}},
    'soma segment': {
        'soma in brain': {},
        'soma in T1': {},
        'soma in T2': {},
        'soma in T3': {},
        'soma in abdominal ganglion': {}},
    'anterior-posterior projection pattern': {
        'descending': {},
        'ascending': {},
        'local': {},
        'intersegmental': {}},
    'left-right projection pattern': {
        'unilateral': {},
        'bilateral': {},
        'midplane': {}},
    'neuron identity': {},
}
FANC_cell_info = cell_info.copy()
FANC_cell_info['publication'] = {
    'Azevedo Lesser Mark Phelps et al. 2022': {},
    'Lesser Azevedo et al. 2023': {},
    'Cheong Boone Bennett et al. 2023': {},
    'Sapkal et al. 2023': {},
    'Yang et al. 2023': {},
    'Dallmann et al. 2023': {}
}

proofreading_notes = [
    'spans neck',
    'no major merge errors',
    'publication quality',
]

# A mapping that tells which CAVE tables are governed by which
# annotation lists/hierarchies
rules_governing_tables = {
    'neuron_information': FANC_cell_info,
    'cell_info': cell_info,
    'proofreading_notes': proofreading_notes,
}


# ------------------------- #


def _dict_to_anytree(dictionary):
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

    return _build_tree(dictionary)

# Convert any hierarchical dictionaries to a tree format that is easier to use
rules_governing_tables = {table_name: _dict_to_anytree(annotations)
                          if isinstance(annotations, dict) else annotations
                          for table_name, annotations in rules_governing_tables.items()}


def print_recognized_annotations(table_name: str = default_table):
    """
    Print the annotation hierarchy for a table.

    Parameters
    ----------
    table_name : str
        The name of the table to print the recognized annotations for.
        OR
        Users will not typically do this, but you can also pass in a list or
        dict specifying the valid annotations directly and it will be used. If
        a dictionary, must map annotation names (str) to anytree.Node objects,
        as output by running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        try:
            annotations = rules_governing_tables[table_name]
        except:
            raise ValueError(f'Table name "{table_name}" not recognized.')
    elif isinstance(table_name, (dict, list)):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    if isinstance(annotations, dict):
        def print_one_tree(annotations, root: str):
            for prefix, _, node in anytree.RenderTree(annotations[root][0]):
                print(f'{prefix}{node.name}')

        for root_node in {anno for anno, nodes in annotations.items()
                          if len(nodes) == 1 and nodes[0].is_root}:
            print_one_tree(annotations, root_node)
    elif isinstance(annotations, list):
        for annotation in annotations:
            print(annotation)


def guess_class(annotation: str, table_name: str = default_table) -> str:
    """
    Look up the parent (or "class") of an annotation based on the rules
    governing the given table. If the annotation is not found or the
    class can't be determined, raise a ValueError.

    Parameters
    ----------
    annotation : str
        The annotation to look up the class of.
    table_name : str
        The name of the table whose rules should be used to look up the
        class of the annotation.
        OR
        Users will not typically do this, but you can also pass in a dict
        specifying the annotation hierarchy/rules directly. The dict must
        map annotation names (str) to anytree.Node objects, as output by
        running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        try:
            annotations = rules_governing_tables[table_name]
        except:
            raise ValueError(f'Table name "{table_name}" not recognized.')
        if not isinstance(annotations, dict):
            raise ValueError(f'"{table_name}" does not use paired annotations.')
    elif isinstance(table_name, dict):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    try:
        annotation_nodes = annotations[annotation]
    except:
        raise ValueError(f'Annotation "{annotation}" not recognized. {help_msg}')

    if len(annotation_nodes) > 1:
        raise ValueError(f'Class of "{annotation}" could not be guessed'
                         f' because it has multiple possible classes. {help_msg}')

    if annotation_nodes[0].is_root:
        raise ValueError(f'"{annotation}" is a base annotation with no class. {help_msg}')
    return annotation_nodes[0].parent.name


def is_valid_annotation(annotation: str or tuple[str, str],
                        table_name: str = default_table,
                        raise_errors: bool = True) -> bool:
    """
    Determine whether an annotation is a recognized/valid annotation
    for the given table.

    Parameters
    ----------
    annotation : str or list/tuple of 2 strs
        The annotation or annotation pair to check the validity of.
    table_name : str
        The name of the table whose rules should be used to determine the
        validity of the annotation.
        OR
        Users will not typically do this, but you can also pass in a list or
        dict specifying the valid annotations directly and it will be used. If
        a dictionary, must map annotation names (str) to anytree.Node objects,
        as output by running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        try:
            annotations = rules_governing_tables[table_name]
        except:
            raise ValueError(f'Table name "{table_name}" not recognized.')
    elif isinstance(table_name, (dict, list)):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    if isinstance(annotations, list):
        if not isinstance(annotation, str):
            raise TypeError('annotation should be a str for this table, but'
                            f' was {type(annotation)}')
        if (annotation not in annotations) and raise_errors:
            raise ValueError(f'Annotation "{annotation}" not recognized. {help_msg}')
        return annotation in annotations

    if raise_errors:
        annotation_class, annotation = parse_annotation_pair(annotation)
    else:
        try:
            annotation_class, annotation = parse_annotation_pair(annotation)
        except:
            return False
    return is_valid_pair(annotation_class, annotation,
                         annotations, raise_errors=raise_errors)


def parse_annotation_pair(annotation: str or tuple[str, str],
                          table_name: str = default_table) -> tuple[str, str]:
    """
    Convert any of the following into a proper (annotation_class, annotation) tuple:
    - A single annotation (str). In this case the annotation_class will be
      guessed based on the rules governing the given table.
    - An annotation_class-annotation pair given as one string with a separator
      (colon, comma, or >) between the annotation_class and annotation.
    - An (annotation_class, annotation) pair given as a 2-length iterable.

    Parameters
    ----------
    annotation : str or list/tuple of 2 strs
        The annotation or annotation pair to parse.

    Returns
    -------
    tuple of 2 strs
        The annotation_class and annotation.
    """
    # If not a str, should be a 2-length iterable
    if not isinstance(annotation, str):
        try:
            annotation_class, annotation = annotation
        except:
            raise TypeError('annotation must be a str or a list/tuple of 2 strs.')
        return annotation_class, annotation

    # If str
    separators = ':>,'
    if not any(separator in annotation for separator in separators):
        annotation_class = guess_class(annotation, table_name)
    else:
        for separator in separators:
            if separator in annotation:
                annotation_class, annotation = annotation.split(separator)
                break
        annotation_class = annotation_class.strip(' ')
        annotation = annotation.strip(' ')

    return annotation_class, annotation


def is_valid_pair(annotation_class: str,
                  annotation: str,
                  table_name: str = default_table,
                  raise_errors: bool = True) -> bool:
    """
    Determine whether `annotation` is a valid annotation for the given
    `annotation_class`, according to the rules for the given table.
    (See https://fanc.community/Neuron-annotations#neuron_information)

    Parameters
    ----------
    annotation_class, annotation : str
        The pair of annotations to check the validity of.
    table_name : str
        The name of the table whose rules should be used to determine the
        validity of the annotation.
        OR
        Users will not typically do this, but you can also pass in a dict
        specifying the valid annotations directly and it will be used. The
        dict must map annotation names (str) to anytree.Node objects, as
        output by running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        try:
            annotations = rules_governing_tables[table_name]
        except:
            raise ValueError(f'Table name "{table_name}" not recognized.')
        if not isinstance(annotations, dict):
            raise ValueError(f'"{table_name}" does not use paired annotations.')
    elif isinstance(table_name, dict):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    if annotation_class == 'neuron identity':
        if annotation in annotations:
            if raise_errors:
                raise ValueError(f'The term "{annotation}" is a class,'
                                 f' not an identity. {help_msg}')
            return False
        return True

    try:
        class_nodes = annotations[annotation_class]
    except:
        if raise_errors:
            raise ValueError(f'Annotation class "{annotation_class}" not'
                             f' recognized. {help_msg}')
        return False
    try:
        annotation_nodes = annotations[annotation]
    except:
        if raise_errors:
            raise ValueError(f'Annotation "{annotation}" not recognized.'
                             f' {help_msg}')
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
    return False


def is_allowed_to_post(segid: int,
                       annotation: str or tuple[str, str],
                       table_name: str = default_table,
                       raise_errors: bool = True) -> bool:
    """
    Determine whether a particular segment is allowed to be annotated
    with the given annotation (or annotation_class+annotation pair, if the
    table uses paired annotations).

    For posting to be allowed:
    - `is_valid_annotation(annotation, table_name)` must return True.
    - The segment must not already have this exact annotation in this table.
    - For tables that use paired annotations (two tag columns), two
      additional constraints apply:
      1. The given annotation pair may not be posted if the segment
      already has any annotation pair with the same annotation_class.
      This and also prevents a class from having multiple subclasses.
      This rule is NOT enforced for a few special annotation_classes
      that are allowed to have many subannotations:
        - 'neuron identity'
        - 'publication'
      2. The given annotation pair may only be posted if its
      annotation_class is at the root of the annotation tree (e.g.
      'primary class'), or if its annotation_class is already an
      annotation on the segment. In other words, allow posts will start
      from the root of the annotation tree, or add detail/subclass
      information to an annotation already on the segment.

    For tables with two tag columns, `annotation` should be in a format
    that `parse_annotation_pair()` can handle, which is:
    - A single annotation (str). In this case the annotation_class will
      be guessed based on the rules governing the given table.
    - An annotation_class-annotation pair given as one string with a separator
      (colon, comma, or >) between the annotation_class and annotation.
    - An (annotation_class, annotation) pair given as a 2-length iterable.

    Returns
    -------
    bool
    - True: This segment MAY be annotated with the annotation or
      annotation_class+annotation pair in the given CAVE table without
      violating any rules about redundancy or mutual exclusivity.
    - False: The proposed annotation or annotation_class+annotation pair
      MAY NOT be posted for this segment without violating a rule.
      If `raise_errors` is True, an exception with an informative error
      message will be raised instead of returning False.
    """
    try:
        annotations = rules_governing_tables[table_name]
    except:
        raise ValueError(f'Table name "{table_name}" not recognized.')

    if not is_valid_annotation(annotation, table_name=table_name,
                               raise_errors=raise_errors):
        return False

    existing_annos = lookup.annotations(segid, source_tables=table_name,
                                        return_details=True)

    if isinstance(annotations, list):
        if annotation in existing_annos.tag.values:
            if raise_errors:
                raise ValueError(f'Segment {segid} already has the'
                                 f' annotation "{annotation}".')
            return False
        return True

    # If we get here, the table uses paired annotations
    if raise_errors:
        annotation_class, annotation = parse_annotation_pair(annotation)
    else:
        try:
            annotation_class, annotation = parse_annotation_pair(annotation)
        except:
            return False

    # Rule 1
    multiple_subclasses_allowed = [
        'neuron identity',
        'publication'
    ]
    if annotation_class in multiple_subclasses_allowed:
        # Check if any tag,tag2 pair is the same as annotation,annotation_class
        if ((existing_annos.tag == annotation) &
            (existing_annos.tag2 == annotation_class)).any():
            if raise_errors:
                raise ValueError(f'Segment {segid} already has this exact'
                                 ' annotation pair.')
            return False
        #------
        # The block of code below is not currently used due to a refactoring of
        # the annotation tree, but it might be useful to bring back later
        #------
        # Multiple subclasses are only allowed if they don't violate the
        # following mutual exclusivity rules. For example, a neuron can't be
        # annotated with both 'unilateral' and 'bilateral'.
        #exclusivity_groups = [
        #    # Exclusivity groups within 'projection pattern':
        #    {'unilateral', 'bilateral'},
        #    {'local', 'intersegmental', 'ascending', 'descending'}
        #]
        #for group in exclusivity_groups:
        #    if annotation in group:
        #        # Check if any annotation in this group already exists
        #        if not existing_annos.loc[existing_annos.tag.isin(group)].empty:
        #            if raise_errors:
        #                raise ValueError(f'Segment {segid} already has an'
        #                                 f' annotation in the group'
        #                                 f' {group}. {help_msg}')
        #            return False
    elif (existing_annos.tag2 == annotation_class).any():
        if raise_errors:
            raise ValueError(f'Segment {segid} already has an annotation with'
                             f' class "{annotation_class}". {help_msg}')
        return False

    # Rule 2
    root_classes = [anno for anno, nodes in annotations.items()
                    if len(nodes) == 1 and nodes[0].is_root]
    if (annotation_class not in root_classes and
            not (existing_annos.tag == annotation_class).any()):
        if raise_errors:
            raise ValueError(f'Segment {segid} must be annotated with'
                             f' "{annotation_class}" before this term can be'
                             f' used as an annotation class. {help_msg}')
        return False

    return True

# detection_manager.py
# Maya Faceit Plugin - Detection Manager
# Converted from Blender to Maya Python 3.11

"""
Detection Manager for target shape names.
Can detect slightly different names by Levenshtein ratio.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple


def get_expression_name_double_entries(
    expression_name: str, 
    expression_list: List[str]
) -> str:
    """
    Add trailing number to double entries.
    Return the name with .001, .002, ... suffix if multiple entries already exist.
    
    Args:
        expression_name: The base expression name
        expression_list: List of existing expression names
        
    Returns:
        Unique expression name with suffix if needed
    """
    expression_name_final = expression_name
    
    if expression_name_final in expression_list:
        max_integer_found = 0
        
        for item_name in expression_list:
            if expression_name_final in item_name:
                # Check for numeric suffix
                if len(item_name) >= 3 and item_name[-3:].isdigit():
                    if item_name[:-4] == expression_name_final:
                        digits = int(item_name[-3:])
                        max_integer_found = max(max_integer_found, digits)
        
        if max_integer_found > 0:
            new_digits = '.' + str(max_integer_found + 1).zfill(3)
        else:
            new_digits = '.001'
        
        expression_name_final += new_digits
    
    return expression_name_final


def detect_shape(
    shape_keys: List[str],
    shape_name: str,
    min_levenshtein_ratio: float = 1.0,
    remove_prefix: str = '',
    remove_suffix: str = ''
) -> str:
    """
    Tries to find the matching shape key by comparing the strings in standardized form.
    
    Args:
        shape_keys: The shape key names to search
        shape_name: The name of the expression to find
        min_levenshtein_ratio: The ratio for fuzzy comparison
        remove_prefix: Prefix to remove from shape names
        remove_suffix: Suffix to remove from shape names
        
    Returns:
        Found shape key name or empty string
    """
    found_shape_key_name = ''
    
    for sk_name in shape_keys:
        st_sk_name = _standardize_shape_name(sk_name)
        st_shape_name = _standardize_shape_name(shape_name)
        
        if st_sk_name == st_shape_name:
            found_shape_key_name = sk_name
            break
        else:
            # Use left and right in full word for better matching
            levenshtein_ratio = _levenshtein_ratio_and_distance(
                st_sk_name.replace('_l', 'left').replace('_r', 'right'),
                st_shape_name.replace('_l', 'left').replace('_r', 'right'),
                ratio_calc=True
            )
            if levenshtein_ratio > min_levenshtein_ratio:
                found_shape_key_name = sk_name
                break
    
    return found_shape_key_name


def _standardize_shape_name(name: str) -> str:
    """
    Standardize a shape name for comparison.
    
    Args:
        name: The shape name to standardize
        
    Returns:
        Standardized name
    """
    # List of chars to replace if they are at the start of a shape name
    starts_with = [
        ('_', ''),
        ('Char', ''),
        ('char', '')
    ]
    
    # Standardize names
    name = (name
        .replace(' ', '_')
        .replace('-', '_')
        .replace('.', '_')
        .replace('____', '_')
        .replace('___', '_')
        .replace('__', '_')
        .replace('Right', '_R')
        .replace('Left', '_L'))
    
    # Replace if name starts with specified chars
    for replacement in starts_with:
        if name.startswith(replacement[0]):
            name = replacement[1] + name[len(replacement[0]):]
    
    # Remove digits from the start
    name_split = name.split('_')
    if len(name_split) > 1 and name_split[0].isdigit():
        name = name_split[1]
    
    # Specific condition
    name_split = name.split('"')
    if len(name_split) > 3:
        name = name_split[1]
    
    # Another specific condition
    if ':' in name:
        for i, split in enumerate(name.split(':')):
            if i == 0:
                name = ''
            else:
                name += split
    
    # Remove S0 from the end
    if name[-2:] == 'S0':
        name = name[:-2]
    
    return name.lower()


def _levenshtein_ratio_and_distance(s: str, t: str, ratio_calc: bool = True) -> float:
    """
    Calculates Levenshtein distance between two strings.
    
    Args:
        s: First string
        t: Second string
        ratio_calc: If True, computes ratio of similarity
        
    Returns:
        Levenshtein ratio or distance
    """
    # Initialize matrix of zeros
    rows = len(s) + 1
    cols = len(t) + 1
    distance = np.zeros((rows, cols), dtype=int)
    
    # Populate matrix with the indices of each character
    for i in range(1, rows):
        distance[i][0] = i
    for k in range(1, cols):
        distance[0][k] = k
    
    # Iterate over the matrix to compute the cost of deletions, insertions, and substitutions
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row - 1] == t[col - 1]:
                cost = 0
            else:
                if ratio_calc:
                    cost = 2
                else:
                    cost = 1
            
            distance[row][col] = min(
                distance[row - 1][col] + 1,           # Deletions
                distance[row][col - 1] + 1,           # Insertions
                distance[row - 1][col - 1] + cost     # Substitutions
            )
    
    if ratio_calc:
        # Computation of the Levenshtein Distance Ratio
        ratio = ((len(s) + len(t)) - distance[row][col]) / (len(s) + len(t))
        return ratio
    
    return float(distance[row][col])


def find_best_match(
    target_name: str,
    candidates: List[str],
    min_ratio: float = 0.8
) -> Tuple[Optional[str], float]:
    """
    Find the best matching candidate for a target name.
    
    Args:
        target_name: The name to match
        candidates: List of candidate names
        min_ratio: Minimum ratio for a match
        
    Returns:
        Tuple of (best_match, best_ratio) or (None, 0.0)
    """
    best_match = None
    best_ratio = 0.0
    
    target_standard = _standardize_shape_name(target_name)
    
    for candidate in candidates:
        candidate_standard = _standardize_shape_name(candidate)
        ratio = _levenshtein_ratio_and_distance(
            target_standard, 
            candidate_standard,
            ratio_calc=True
        )
        
        if ratio > best_ratio and ratio >= min_ratio:
            best_ratio = ratio
            best_match = candidate
    
    return best_match, best_ratio


def get_expression_name_double_entries_maya(
    expression_name: str,
    existing_names: List[str]
) -> str:
    """
    Maya-specific version of expression name deduplication.
    
    Args:
        expression_name: The base expression name
        existing_names: List of existing expression names
        
    Returns:
        Unique expression name with suffix if needed
    """
    return get_expression_name_double_entries(expression_name, existing_names)
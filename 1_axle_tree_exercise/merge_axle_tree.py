# #!/usr/bin/env python3
import json
from PIL import Image, ImageDraw
from annotate import annotate

# -------------------------------------------------------------------------------------------------------------------- #

def open_json_from_file(json_path):
    """
    Loads a json from a file path.

    :param json_path: path to the json file
    :return: the loaded json
    """
    try:
        with open(json_path) as json_file:
            json_data = json.load(json_file)
    except:
        print(f"Could not open file {json_path} in json format.")
        raise

    return json_data


def save_json_to_file(json_data, json_path):
    """
    Saves a json to a file.

    :param json_data: the actual json
    :param json_path: path to the json file
    :return:
    """
    try:
        with open(json_path, 'w') as json_file:
            json.dump(json_data, json_file)
    except:
        print(f"Could not save file {json_path} in json format.")
        raise

    return


def pretty_print(inline_json):
    """
    Prints a json in the command interface in easily-readable format.

    :param inline_json:
    :return:
    """
    print(json.dumps(inline_json, indent=4, sort_keys=True))
    return

# -------------------------------------------------------------------------------------------------------------------- #
def is_superposed(rect_1, rect_2):
    """
    Function used to determine if two boxes overlap each other
    :param rect_1: box_1
    :param rect_2: box_2
    :return: bool
    """
    xmin_1, xmax_1, ymin_1, ymax_1 = rect_1
    xmin_2, xmax_2, ymin_2, ymax_2 = rect_2
    if xmax_1 < xmin_2 or xmax_2 < xmax_1:
        return False
    if ymax_1 < ymin_2 or ymax_2 < ymin_1:
        return False
    return True

def fusion(rect_1,rect_2):
    """
    We take two boxes and merge them into one big enough to regroup them.
    :param rect_1: box_1
    :param rect_2: box_2
    :return: A box large enough to contain both
    """
    xmin_1, xmax_1, ymin_1, ymax_1 = rect_1
    xmin_2, xmax_2, ymin_2, ymax_2 = rect_2
    new_xmin = min(xmin_1, xmin_2)
    new_xmax = max(xmax_1, xmax_2)
    new_ymin = min(ymin_1, ymin_2)
    new_ymax = max(ymax_1, ymax_2)
    return (new_xmin, new_xmax, new_ymin, new_ymax)

def to_group(box_list):
    """
    :param box_list: list of boxes that represent the single_axles in the annotation JSON
                         in which we will look for potential grouped ones
    :return: Dictionnary with the lists of the final singles axles and grouped axles
            {"single_axles":  list of all the boxes representing the single_axles to be annotated,
             "grouped_axles": list of all the boxes representing the grouped_axles to be annotated}

    We create the grouped_axles using the superposed function, if the boxes are on top of one another then we group them
    """
    single_axles = box_list.copy()
    grouped_axles = []
    groups = {}

    for rect_1 in single_axles + grouped_axles:
        for rect_2 in single_axles + grouped_axles:
            if rect_1 != rect_2:
                if is_superposed(rect_1, rect_2) or is_superposed(rect_2, rect_1):
                    new_rect = fusion(rect_1, rect_2)
                    grouped_axles.append(new_rect)
                    if rect_1 in single_axles:
                        single_axles.remove(rect_1)
                    if rect_1 in grouped_axles:
                        grouped_axles.remove(rect_1)
                    if rect_2 in single_axles:
                        single_axles.remove(rect_2)
                    if rect_2 in grouped_axles:
                        grouped_axles.remove(rect_2)

    # We make sure the list doesn't contain doubles
    single_axles = list(set(single_axles))
    grouped_axles = list(set(grouped_axles))

    groups["single_axle"] = single_axles
    groups["grouped_axles"] = grouped_axles

    return groups

def merge_axle_trees(data):
    """
    Take an annotation and return an updated annotation with axle tree areas.
    :param annotation: annotation json without merged axle
    :return: annotation json with axle tree areas
    """
    for data_image in data['images']: #On parcourt toutes les images
        single_axles = []
        grouped_axles = []
        other_annotations = []

        for annotation in data_image['annotated_regions']:
            #On va chercher toutes les annotations et récupérer les rectangles des single_axle
            if annotation.get("tags") == ["single_axle"]:
                xmin = float(annotation['region']['xmin'])
                xmax = float(annotation['region']['xmax'])
                ymin = float(annotation['region']['ymin'])
                ymax = float(annotation['region']['ymax'])
                rect = (xmin, xmax, ymin, ymax)
                single_axles.append(rect)

        #We only keep the non axles boxes as they will be worked on separatly
        for annotation in data_image['annotated_regions']:
            if annotation.get("tags") != ["single_axle"]:
                other_annotations.append(annotation)
        data_image["annotated_regions"] = other_annotations #We take out the axles

        #We call the group function that will create the different boxes of single_axles and grouped_axles
        groups = to_group(single_axles)

        #Wego through the groups dictionnary and create the corresponding annotation
        for tag in groups.keys():
            for rect in groups[tag]:
                xmin, xmax, ymin, ymax = rect
                new_annotation = {'tags': [tag],
                                  'region_type': 'Box',
                                  'region': {
                                      'xmin': xmin, 'xmax': xmax,
                                      'ymin': ymin, 'ymax': ymax
                                  }
                                  }
                data_image['annotated_regions'].append(new_annotation)

    return data

if __name__ == '__main__':
    annotate('annotations.json', 'default')
    # Load annotations from json file
    json_data = open_json_from_file('annotations.json')
    # Merge
    json_data = merge_axle_trees(json_data)
    #pretty_print(json_data)
    # Saves new annotations to json file
    save_json_to_file(json_data, 'new_annotations.json')
    annotate('new_annotations.json', 'merged')





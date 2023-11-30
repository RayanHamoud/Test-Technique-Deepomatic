# #!/usr/bin/env python3
import numpy as np
import json
import time
from annotate import annotate
from shapely import Polygon
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #

def iou(box_1, box_2):
    """
    Calculates the Intersection Over Union for the two boxes
    :param box_1: first box in the format {
            "xmin": _,
            "xmax": _,
            "ymin": _,
            "ymax": _
          }
    :param box_2: same format
    :return: Surface(intersection)/Surface(union)
    """
    poly1 = Polygon([(box_1['xmin'], box_1['ymin']),
                     (box_1['xmin'], box_1['ymax']),
                     (box_1['xmax'], box_1['ymax']),
                     (box_1['xmax'], box_1['ymin'])])

    poly2 = Polygon([(box_2['xmin'], box_2['ymin']),
                     (box_2['xmin'], box_2['ymax']),
                     (box_2['xmax'], box_2['ymax']),
                     (box_2['xmax'], box_2['ymin'])])

    intersection_surface = poly1.intersection(poly2).area
    union_surface = poly1.union(poly2).area

    res = intersection_surface / union_surface
    return res

def evaluate_image(annotations, predictions, threshold, Jaccard_min=0.5):
    """
    Take a list of annotations and predictions, a threshold, and returns
    the number of true positives, false positives, and false negatives.

    :param annotations: the json containing the annotations
    :param predictions: the json containing the predictions
    :param threshold: the threshold used to select the boxes to evaluate
    :param Jaccard_min: the IoU threshold used to evaluate
    :return: (true_positives, false_negatives, false_positives)
    """
    annotations_copy = annotations.copy()
    predictions_copy = predictions.copy()

    true_positives = 0
    false_negatives = 0
    false_positives = 0

    for annotation in annotations:
        true_box = annotation['region']
        candidates = []
        for prediction in predictions:
            if prediction["score"] > threshold:
                candidate_box = prediction['region']
                iou_score = iou(candidate_box, true_box)
                if iou_score >= Jaccard_min:
                    candidates.append((prediction, iou_score))
        if not candidates:
            false_negatives += 1
            annotations_copy.remove(annotation)
        else:
            best_prediction, best_score = max(candidates, key=lambda item: item[1])
            true_positives += 1
            predictions_copy.remove(best_prediction)
            annotations_copy.remove(annotation)

    false_positives = len(predictions_copy)
    return true_positives, false_negatives, false_positives


# --------------------------------------------------------------------------- #

def evaluate_pr_naive(annotations_json, predictions_json, N=10, Jaccard_min=0.5):
    """
    Take a list of annotations and predictions, the number of tresholds
    to test, and returns the precision and recall at each threshold. In
    the following form:

    [{
        "precision": 0.2,
        "recall": 0.9,
        "threshold": 0.1
    }, {
        "precision": 0.3,
        "recall": 0.8,
        "threshold": 0.2
    }, ...]

    :param annotations_json: the json containing the annotations
    :param predictions_json: the json containing the predictions
    :param N: the numbers of thresholds to test
    :param Jaccard_min: the IoU threshold used to evaluate
    :return: the list of computed metrics
    precision = TP/(TP+FP)
    recall = TP/(TP+FN)
    These metrics are calculated on the whole dataset
    """
    result_list = []
    thresholds = [k/N for k in range(0, N)]

    for threshold in thresholds:
        to_append = {}
        total_TP = 0
        total_FP = 0
        total_FN = 0

        for image_real, image_pred in zip(annotations_json['images'], predictions_json['images']):
            real_annotations = image_real['annotated_regions']
            pred_annotations = image_pred['annotated_regions']
            TP, FN, FP = evaluate_image(real_annotations, pred_annotations, threshold)
            total_TP += TP
            total_FP += FP
            total_FN += FN

        precision = total_TP/(total_TP + total_FP)
        recall = total_TP/(total_TP + total_FN)
        to_append['precision'] = precision
        to_append['recall'] = recall
        to_append['threshold'] = threshold
        result_list.append(to_append)

    return result_list



def evaluate_pr(annotations_json, predictions_json, N=10, Jaccard_min=0.5):
    """
    Optimized version: minimize the amount of computation.
    Take a list of annotations and predictions, the number of tresholds
    to test, and returns the precision and recall at each threshold. In
    the following form:

    [{
        "precision": 0.2,
        "recall": 0.9,
        "threshold": 0.1
    }, {
        "precision": 0.3,
        "recall": 0.8,
        "threshold": 0.2
    }, ...]
    :param annotations_json: the json containing the annotations
    :param predictions_json: the json containing the predictions
    :param N: the numbers of thresholds to test
    :param Jaccard_min: the IoU threshold used to evaluate
    :return: the list of computed metrics
    La version optimisée va utiliser numpy pour éviter les boucles for et accélérer les calculs, et on ne va pas étudier
    tous les thresholds mais uniquement ceux qui sont supérieurs au plus petit score
    """
    result_list = []

    true_annotations = annotations_json['images']
    pred_annotations = predictions_json['images']


    min_score = min([[annot_pred['score'] for annot_pred in img['annotated_regions'] ]for img in pred_annotations])[0]
    k_min = int(min_score*N)-1

    thresholds = [k / N for k in range(k_min, N)]

    for threshold in thresholds:
        evaluations = np.array([evaluate_image(img_annot['annotated_regions'],
                                               img_pred['annotated_regions'],
                                               threshold)\
                                for img_annot, img_pred in zip(true_annotations, pred_annotations)])

        total_TP = evaluations[:, 0].sum()
        total_FN = evaluations[:, 1].sum()
        total_FP = evaluations[:, 2].sum()

        precision = total_TP / (total_TP + total_FP)
        recall = total_TP / (total_TP + total_FN)

        result_list.append({
            "precision": precision,
            "recall": recall,
            "threshold": threshold
        })
    result_list = k_min*[result_list[0]]+result_list

    return result_list


if __name__ == '__main__':
    annotate('groundtruth.json', 'truth')
    annotate('predictions.json', 'prediction')
    # Load annotations from json file
    groundtruth = open_json_from_file('groundtruth.json')
    predictions = open_json_from_file('predictions.json')
    print(type(groundtruth['images']))
    # Evaluate

    for img_truth, img_prediction in zip(groundtruth['images'], predictions['images']):
        annotations_list = img_truth['annotated_regions']
        predictions_list = img_prediction['annotated_regions']
        TP, FN, FP = evaluate_image(annotations_list, predictions_list, 0.2)
        print(f"Image '{img_truth['location']}'\n\t- TP:{TP}  \n\t- FN:{FN} \n\t- FP:{FP} ")

    # Compare evaluate_pr_naive and evaluate_pr
    T0 = time.time()
    evaluate_pr_naive(groundtruth, predictions, N=10, Jaccard_min=0.5)
    T1 = time.time()
    evaluate_pr(groundtruth, predictions, N=10, Jaccard_min=0.5)
    T2 = time.time()
    print(f"Naive version computed in {round(T1-T0, 2)}s")
    print(f"Optimized version computed in {round(T2-T1, 2)}s")



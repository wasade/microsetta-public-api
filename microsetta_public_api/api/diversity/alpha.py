from flask import jsonify as flask_jsonify
from microsetta_public_api.models._alpha import Alpha
from microsetta_public_api.repo._alpha_repo import AlphaRepo


def jsonify(*args, **kwargs):
    return flask_jsonify(*args, **kwargs)


def get_alpha(sample_id, alpha_metric):
    alpha_repo = AlphaRepo()
    if not all(alpha_repo.exists([sample_id], alpha_metric)):
        return jsonify(error=404, text="Sample ID not found."),\
               404
    alpha_series = alpha_repo.get_alpha_diversity([sample_id],
                                                  alpha_metric)
    alpha_ = Alpha(alpha_series)
    alpha_data = alpha_.get_group_raw().to_dict()
    ret_val = {
        'sample_id': sample_id,
        'alpha_metric': alpha_data['alpha_metric'],
        'data': alpha_data['alpha_diversity'][sample_id],
    }

    return jsonify(ret_val), 200


def alpha_group(body, alpha_metric, summary_statistics=True,
                percentiles=None, return_raw=False):
    if not (summary_statistics or return_raw):
        # swagger does not account for parameter dependencies, so we should
        #  give a bad request error here
        return jsonify(
            error=400, text='Either `summary_statistics`, `return_raw`, '
                            'or both are required to be true.'
            ), 400

    sample_ids = body['sample_ids']

    alpha_repo = AlphaRepo()

    # figure out if the user asked for a metric we have data on
    available_metrics = alpha_repo.available_metrics()
    if alpha_metric not in available_metrics:
        return jsonify(error=404, text=f"Requested metric: '{alpha_metric}' "
                                       f"is unavailable. Available metrics: "
                                       f"{available_metrics}"), 404

    # make sure all of the data the samples the user asked for have values
    # for the given metric
    missing_ids = [id_ for id_ in sample_ids if
                   not alpha_repo.exists(id_, alpha_metric)]
    if len(missing_ids) > 0:
        return jsonify(missing_ids=missing_ids,
                       error=404, text=f"Sample ID(s) not found for "
                                       f"metric: {alpha_metric}"),\
                       404

    # retrieve the alpha diversity for each sample
    alpha_series = alpha_repo.get_alpha_diversity(sample_ids,
                                                  alpha_metric,
                                                  )
    alpha_ = Alpha(alpha_series, percentiles=percentiles)
    alpha_data = dict()

    if return_raw:
        # not using name right now, so give it a placeholder name
        alpha_values = alpha_.get_group_raw(name='').to_dict()
        del alpha_values['name']
        alpha_data.update(alpha_values)
    if summary_statistics:
        # not using name right now, so give it a placeholder name
        alpha_summary = alpha_.get_group(name='').to_dict()
        del alpha_summary['name']
        alpha_data.update({'alpha_metric': alpha_summary.pop('alpha_metric')})
        alpha_data.update({'group_summary': alpha_summary})

    response = jsonify(alpha_data)
    return response, 200


def available_metrics_alpha():
    alpha_repo = AlphaRepo()
    ret_val = {
        'alpha_metrics': alpha_repo.available_metrics(),
    }

    return jsonify(ret_val), 200
from requests import request, ConnectionError, ReadTimeout
import os
from .config import ET_PROJECTS

_available_version_checked = False

def _etrequest(endpoint, method="get", **kwargs):
    if kwargs.get('timeout') is None:
        kwargs['timeout'] = 5
    try:
        res = request(method, endpoint, **kwargs)
    except ConnectionError:
        raise RuntimeError("Connection to server could not be made")
    except ReadTimeout:
        raise RuntimeError(
            "No response from server in {timeout} seconds".format(
                timeout=kwargs.get('timeout')
            )
        )
    res.raise_for_status()
    return res


def get_project(repo, **rargs):
    """
    Fetch latest version from server.

    Parameters
    ==========
    repo : str
        GitHub repository as <owner>/<project>
    **rargs
        Request keyword arguments

    Returns
    =======
    response
        Dictionary with `version` field
    """
    if "NO_ET" in os.environ:
        return None
    if "/" not in repo:
        raise ValueError("Invalid repository")
    res = _etrequest(ET_PROJECTS.format(repo=repo), **rargs)
    return res.json(encoding="utf-8")


def check_available_version(project, lgr=None, raise_exception=False):
    """A helper to check (and report) if newer version of project is available
    Should be ok to execute multiple times, it will be checked only one time
    Parameters
    ----------
    project: str
      as on GitHub (e.g., sensein/etelemetry-client. Releases will be checked
    """
    global _available_version_checked
    if _available_version_checked:
        return
    _available_version_checked = True

    if lgr is None:
        import logging
        lgr = logging.logger('etlogger')

    # TODO: run in a separate thread
    try:
        import etelemetry
    except ImportError as exc:
        lgr.debug(
            "Cannot check latest available version for %s: %s",
            project, exc
        )
        return

    from pkg_resources import parse_version
    from . import __version__

    latest = {"version": "Unknown", "bad_versions": []}
    try:
        ret = etelemetry.get_project(project)
    except Exception as e:
        lgr.debug("Could not check %s for version updates: %s", project, e)
        return None
    finally:
        if ret:
            latest.update(**ret)
            local_version = parse_version(__version__)
            remote_version = parse_version(latest["version"])
            if  local_version < remote_version:
                lgr.info(f"A newer version ({latest[version]}) of {project} "
                         f"is available. You are using {__version__}")
            elif remote_version < local_version:
                lgr.debug(
                    "Running a newer version (%s) of %s than available (%s)",
                    __version__, project, latest["version"])
            else:  # ==
                lgr.debug("No newer (than %s) version of %s found available",
                          __version__, project)
            if latest["bad_versions"] and any(
                    [
                        local_version == parse_version(ver)
                        for ver in latest["bad_versions"]
                    ]
            ):
                message = f"You are using a version of {project} with a " \
                          f"critical bug. Please use a different version."
                if raise_exception:
                    raise RuntimeError(message)
                else:
                    lgr.critical(message)
    return latest

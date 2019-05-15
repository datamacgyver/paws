from pathlib import Path
import shutil


def zip_to(to_zip, zip_name, overwrite=False):
    """
    Zip a directory to a specified location.

    Parameters
    ----------
    to_zip: Path or str
        Path of a directory to make an archive of.
    zip_name: Path or str
        Path or str of location to store the archive. This must
        include the filename and extension.
    overwrite: bool, optional
        If zip_name already exists, should it be overwritten? False
        by default.

    Returns
    -------
    zip_name: Path
        Path representation of zip_name.
    """
    to_zip = Path(to_zip)
    zip_name = Path(zip_name)

    zipped = shutil.make_archive(to_zip, "zip", root_dir=to_zip)

    if overwrite and zip_name.exists():
        zip_name.unlink()
    Path(zipped).rename(zip_name)
    return zip_name

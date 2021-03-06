# coding=utf-8

"""
Copyright (c) 2016, 2017 FZI Forschungszentrum Informatik am Karlsruher Institut für Technologie

This file is part of SNAPE.

SNAPE is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SNAPE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SNAPE.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import traceback
import codecs
from config import ROOT
import portalocker as plocker
import re
import time
from shutil import rmtree


def __natural_sort(l):
    """
    Synopsis:
        Takes a list and returns it in natural sorted order.
        E.g.: [Obj1, Obj7, Obj3, Obj13, Obj11] -> [Obj1, Obj3, Obj7, Obj11, Obj13]
    :param l: list to be sorted
    :returns l: sorted list
    """
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return sorted(l, key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)])


def __secure_filename(filename, allowed = ''):
    """
    Synopsis:
        Takes a filename and replaces all characters that are 'forbidden' with an underscore.
        By default, only alphanumeric characters are allowed.
    :param filename: filename to be sanitized
    :param allowed: an iterable containing all non-alphanumeric characters which should not be replaced
    :returns sanitized_filename: string
    """
    snames = filename.split('.')
    if len(snames) >= 2:
        front = "".join(snames[i] for i in range(len(snames) - 1))
        return "".join([c if c.isalpha() or c.isdigit() or c in allowed
                        else '_'
                        for c in front]).rstrip() \
            + '.' + "".join([c if c.isalpha() or c.isdigit() or c in allowed
                             else '_'
                             for c in snames[-1]]).rstrip()
    else:
        return "".join([c if c.isalpha() or c.isdigit() or c in allowed else '_' for c in filename]).rstrip()


def __secure_foldername(foldername):
    """
    Synopsis:
        Takes a foldername and replaces all characters that are 'forbidden' with an underscore.
        Only alphanumeric characters are allowed.
    :param foldername: foldername to be sanitized
    :returns sanitized_foldername: string
    """
    return "".join([c if c.isalpha() or c.isdigit() else '_' for c in foldername]).rstrip()


def check_project_exists(project_id):
    """
    Synopsis:
        Checks database for a project with the given ID, and returns the result.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be searched
    :returns project_found: boolean
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        try:
            for roots, dirs, files in os.walk(r'database', topdown = False):
                if __secure_foldername(unicode(project_id)) in dirs:
                    return True
            return False
        except OSError:
            traceback.print_exc()
            raise OSError


def check_revision_exits(project_id, revision_id):
    """
    Synopsis:
        Checks database project folder for a revision with the given ID, and returns the result.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be searched
    :param revision_id: ID of the revision to be searched for
    :returns revision_found: boolean
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        try:
            for roots, dirs, files in os.walk(os.path.join('database', __secure_foldername(unicode(project_id))),
                                              topdown = False):
                if __secure_filename('v' + unicode(revision_id)) in dirs:
                    return True
            return False
        except OSError:
            traceback.print_exc()
            raise OSError


def get_folder_size(root = '.'):
    """
    Synopsis:
        Checks database for the size of a folder.
        This function claims the *db.lock* system lock.
    :param root: path of folder to be checked.
    :returns total_size: integer
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(root):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size


def get_project_models(project_id):
    """
    Synopsis:
        Returns the relative paths to the model files of a given project.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be searched
    :returns mdj_files: list of strings
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)

        mdj_files = []
        try:
            for roots, dirs, files in os.walk(os.path.join('database', __secure_foldername(unicode(project_id))),
                                              topdown = False):
                for dir_name in __natural_sort(dirs):
                    if dir_name not in ['cache', 'statistics']:
                        for r, d, f in os.walk(os.path.join('database', __secure_foldername(unicode(project_id)),
                                                            dir_name), topdown = False):
                            for file_name in f:
                                mdj_files.append(os.path.join('database', __secure_foldername(unicode(project_id)),
                                                              dir_name, file_name))
        except OSError:
            traceback.print_exc()
            raise OSError

        return mdj_files


def get_project_info(project_id):
    """
    Synopsis:
        Returns information about a projects revisions.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be searched
    :returns ids: list of revision IDs
    :returns model_metadata: dictionary with revisions as keys and
        triples (file name, file size, file creation time) as values
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        ids = list()
        model_metadata = dict()
        try:
            for roots, dirs, files in os.walk(os.path.join('database', __secure_foldername(unicode(project_id))),
                                              topdown = False):
                for dir_name in __natural_sort(dirs):
                    try:
                        ids.append(int(dir_name[1:]))
                        for r, d, f in os.walk(os.path.join('database', __secure_foldername(unicode(project_id)),
                                                            dir_name), topdown = False):
                            file_time = time.ctime(os.path.getmtime(r + os.path.sep + f[0]))
                            file_size_kb = str(os.stat(r + os.path.sep + f[0]).st_size // 1024 + 1) + 'KB'
                            model_metadata[int(dir_name[1:])] = (f[0], file_size_kb, file_time)
                            break
                    except Exception:
                        pass
        except OSError:
            traceback.print_exc()
            raise OSError

        return ids, model_metadata


def create_project(project_id):
    """
    Synopsis:
        Creates a new database folder for a project with the given ID.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be created
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        if type(project_id) is not unicode:
            project_id = unicode(project_id)
        project_id = __secure_foldername(project_id)
        if not os.path.exists(os.path.join('database', __secure_foldername(unicode(project_id)))):
            os.makedirs(os.path.join('database', __secure_foldername(unicode(project_id))))


def delete_project(project_id):
    """
    Synopsis:
        Deletes a database folder of the project with the given ID
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be deleted
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        project_id = __secure_foldername(unicode(project_id))
        for root, dirs, files in os.walk(os.path.join('database', __secure_foldername(unicode(project_id))),
                                         topdown = False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

        os.rmdir(os.path.join('database', __secure_foldername(unicode(project_id))))


def add_revision(project_id, model_file, filename = None):
    """
    Synopsis:
        Adds a new revision to the project database folder with the given ID.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project
    :param model_file: file to be saved
    :param filename: if provided, this is used internally instead of the files name attribute
    :returns version_number: integer
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        project_id = __secure_foldername(unicode(project_id))
        version_number = 1

        for root, dirs, files in os.walk(os.path.join('database', __secure_foldername(unicode(project_id))),
                                         topdown = False):
            for name in dirs:
                if name not in ['cache', 'statistics'] and int(name[1:]) >= version_number:
                    version_number = int(name[1:]) + 1

        try:
            os.makedirs(os.path.join('database', project_id, 'v%i' % version_number))
            os.chdir(os.path.join('database', project_id, 'v%i' % version_number))
            if filename:
                file_obj = codecs.open(__secure_filename(filename), 'w')
                for line in model_file:
                    file_obj.write(line)
                file_obj.close()
            else:
                model_file.save(os.path.join(os.path.join('database', project_id, 'v%i' % version_number),
                                             __secure_filename(model_file.filename.encode('utf-8'))))
        finally:
            os.chdir(ROOT)
        return version_number


def delete_revision(project_id, version_number):
    """
    Synopsis:
        Removes a revision with the given version number from the database folder of the specified project.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project
    :param version_number: ID of the revision to be deleted
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        project_id = __secure_foldername(unicode(project_id))
        for root, dirs, files in os.walk(os.path.join('database', project_id, 'v%i' % version_number),
                                         topdown = False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

        os.rmdir(os.path.join('database', project_id, 'v%i' % version_number))


def add_statistics(project_id, stat_files_paths):
    """
    Synopsis:
        Takes a list of paths to project statistics files and moves them to their proper destination
        inside the project database folder of the specified project.
    :param project_id: ID of the project
    :param stat_files_paths: list of paths to the statistics files to be transferred to a project
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        project_id = __secure_foldername(unicode(project_id))

        if not os.path.isdir(os.path.join('database', project_id, 'statistics')):
            os.mkdir(os.path.join('database', project_id, 'statistics'))
        for path in stat_files_paths:
            if os.path.isfile(os.path.join('database', project_id, 'statistics', os.path.split(path)[-1])):
                os.remove(os.path.join('database', project_id, 'statistics', os.path.split(path)[-1]))
            os.rename(path, os.path.join('database', project_id, 'statistics', os.path.split(path)[-1]))


def get_project_statistics(project_id):
    """
    Synopsis:
        Returns a list of paths to all statistics files of a given project
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be searched
    :returns statistics_paths: list of strings
    """
    with open(os.path.join('database', 'db.lock'), 'a', 0) as db_lock:
        plocker.lock(db_lock, plocker.LOCK_EX)
        project_id = __secure_foldername(unicode(project_id))

        statistics_paths = list()

        stat_paths = [os.path.join('database', project_id, 'statistics', 'complexity.png'),
                      os.path.join('database', project_id, 'statistics', 'quantity.png')]

        for path in stat_paths:
            if os.path.isfile(path):
                statistics_paths.append(path)

        return statistics_paths


def invalidate_cache(project_id):
    """
    Synopsis:
        Deletes the cache of a database project folder.
        This function claims the *cache.lock* system lock.
    :param project_id: ID of the project to be searched
    """
    with open('cache.lock', 'a', 0) as cache_lock:
        plocker.lock(cache_lock, plocker.LOCK_EX)
        if os.path.isdir(os.path.join('database', project_id, 'cache')):
            rmtree(os.path.join('database', project_id, 'cache'))


def build_cache(project_id, diagram_id):
    """
    Prerequisite:
        Project has been rendered into root.
        Only use when holding *cache.lock* system lock.
    Synopsis:
        Builds a projects cache and removes rendered images from root.
        This function claims the *db.lock* system lock.
    :param project_id: ID of the project to be searched
    :param diagram_id: ID of the diagram used for rendering
    """
    os.makedirs(os.path.join('database', project_id, 'cache', diagram_id))
    for file_name in os.listdir('./'):
        if file_name.startswith('dfv_') and file_name.endswith('.png'):
            os.rename(file_name, os.path.join('database', project_id, 'cache',
                                              diagram_id, file_name))
        elif file_name.startswith('temp_dot_file') and file_name.endswith('.txt'):
            os.rename(file_name, os.path.join('database', project_id, 'cache',
                                              diagram_id,
                                              file_name.replace('temp_dot_file', 'graph')
                                              .replace('txt', 'dot')))


def get_cache_filepath(frame, project_id, diagram_id):
    """
    Prerequisite:
        Only use when holding *cache.lock* system lock. DO NOT LOCK CACHE HERE.
    Synopsis:
        Returns path of cached render (subject to the given diagram_id) for the given frame of a project.
    :param project_id: ID of the project to be searched
    :param frame: frame index to be returned
    :param diagram_id: ID of the diagram used for rendering
    :returns revision_found: boolean
    """
    if os.path.isdir(os.path.join('database', project_id, 'cache', diagram_id)):
        pad_h = '' if frame // 100 != 0 or frame > 999 else '0'
        pad_t = '' if frame // 10 != 0 or frame > 999 else '0'
        framepath = os.path.join('database', project_id, 'cache', diagram_id,
                                 'dfv_%s%s%i.png' % (pad_h, pad_t, frame))
        if os.path.isfile(framepath):
            return framepath
    return ''


if __name__ == '__main__':
    pass

# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Contains the WithCustomRestrictions mixin"""
import logging

from datetime import datetime
from datetime import date

from ggrc.models import reflection
from ggrc.models.mixins.statusable import Statusable
from ggrc.rbac import permissions
from ggrc.utils import benchmark

logger = logging.getLogger(__name__)


class WithCustomRestrictions(object):
  """Mixin for SOX302 assessments that have restricted permissions for
  users with Assignees role"""

  _api_attrs = reflection.ApiAttributes(
      reflection.Attribute('_is_sox_restricted', create=False, update=False),
      reflection.Attribute('_readonly_fields', create=False, update=False),
  )

  _restricted_user_roles = ["Assignees"]

  _in_progress_restrictions = (
      "title"
  )

  _done_state_restrictions = _in_progress_restrictions + (
      "slug"
  )

  _restriction_condition = {
      "status": {
          Statusable.START_STATE: _in_progress_restrictions,
          Statusable.PROGRESS_STATE: _in_progress_restrictions,
          Statusable.DONE_STATE: _in_progress_restrictions,
          Statusable.VERIFIED_STATE: _done_state_restrictions,
          Statusable.FINAL_STATE: _done_state_restrictions,
          Statusable.DEPRECATED: _done_state_restrictions,
      }
  }

  @staticmethod
  def _get_user_roles(obj, user):
    """Get all roles with update access for user"""
    from ggrc_basic_permissions import permissions_for_object

    roles = []
    perm = permissions_for_object(user, obj)
    for role_name, perm in perm.items():
      if perm['update']:
        roles.append(role_name)
    return roles

  def is_user_role_restricted(self, user):
    """Check if user (1) has Assignee role for Assessment and (2) does not
    have propagated roles"""
    with benchmark("Check user permissions for SOX302"):
      if permissions.has_system_wide_update():
        return False

      assmnt_roles = self._get_user_roles(self, user)
      if assmnt_roles == self._restricted_user_roles:
        return True
      return False

  def _is_sox_restricted(self):
    """Check if user has restricted access for the object {self}"""
    if not hasattr(self, "sox_302_enabled"):
      return False

    user = permissions.get_user()
    return self.sox_302_enabled and self.is_user_role_restricted(user)

  def _readonly_fields(self):
    # type: () -> tuple
    """Get list of all readonly fields for object {self} for user current
    user"""
    if not self._is_sox_restricted:
      return tuple()
    for field_name, restrictions_dict in self._restriction_condition.items():
      obj_state = getattr(self, field_name)
      for field_value, read_only_fields in restrictions_dict.items():
        if (isinstance(field_value, tuple) and obj_state in field_value) or \
           obj_state == field_value:
          return read_only_fields
    return tuple()

  def _are_lists_equal(self, list1, list2):
    """Compare two lists and return a result: True if lists do not have
    updated values."""
    if len(list1) != len(list2):
      return False
    if not list1:
      return True
    if isinstance(list1[0], dict):
      # we need it to have sorted values that we able to compare
      dict1 = {item.get('id'): item for item in list1}
      dict2 = {item.get('id'): item for item in list2}
      return self._are_dicts_equal(dict1, dict2)
    return sorted(list1) == sorted(list2)

  def _are_dicts_equal(self, dict1, dict2):
    """Compare two dictionaries and return a result: True if dictionaries do
    not have different key-value pair. Comparison does not count new key-value
    pairs that does not contain one of dictionaries."""
    if len(dict1.keys()) > len(dict2.keys()):
      dict1, dict2 = dict2, dict1
    for field, value in dict1.items():
      if str(field).startswith("_"):
        # Debug information does not related to model
        continue
      if field in dict2:
        if not self._are_fields_equal(dict2[field], value):
          return False
    return True

  def _are_fields_equal(self, obj_field, src_field):
    """Compare tho objects and their content. If an object is a type of
     List of Dict, then each item of it will be compared. Returns True if
     objects are equal to each other."""
    if isinstance(obj_field, dict):
      return self._are_dicts_equal(obj_field, src_field)
    elif isinstance(obj_field, list):
      return self._are_lists_equal(obj_field, src_field)

    obj_field = self.convert_to_string(obj_field)
    src_field = self.convert_to_string(src_field)

    return obj_field == src_field

  @staticmethod
  def convert_to_string(custom_value):
    """Convert custom types to string to simplify comparison"""
    if isinstance(custom_value, datetime):
      return custom_value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(custom_value, date):
      return custom_value.strftime("%Y-%m-%d")
    return custom_value

  def is_updating_readonly_fields(self, src):
    """Check is {src} going to update fields that is readonly for current
    {user}"""
    ro_fields = tuple([field for field in self._readonly_fields()
                       if field not in self.mapping_restrictions()])
    json_obj = self.log_json()
    for field in ro_fields:
      if not self._are_fields_equal(json_obj.get(field, None),
                                    src.get(field, None)):
        return True
    return False

  def mapping_restrictions(self):
    """List of models names that mapping restricted for"""
    return tuple([ro_field for ro_field
                  in self._readonly_fields()
                  if ro_field.startswith("map: ")])

  def is_mapping_restricted(self, obj):
    """Check if restricted mapping for {obj}"""
    if "map: {}".format(obj.__class__.__name__) in self.mapping_restrictions():
      return True
    return False
/*!
 Copyright (C) 2017 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

(function (can, GGRC) {
  'use strict';

  var template = can.view(GGRC.mustache_path +
    '/components/advanced-search/advanced-search-mapping-criteria.mustache');

  var viewModel = can.Map.extend({
    define: {
      criteria: {
        type: '*',
        Value: can.Map,
        set: function (criteria) {
          if (!criteria.filter) {
            criteria.attr('filter',
              GGRC.Utils.AdvancedSearch.create.attribute());
          }
          return criteria;
        }
      }
    },
    modelName: null,
    root: false,
    availableAttributes: [],
    mappingTypes: function () {
      var mappings = GGRC.Mappings
        .get_canonical_mappings_for(this.attr('modelName'));
      var types = _.filter(_.sortBy(_.compact(_.map(_.keys(mappings),
        function (mapping) {
          return CMS.Models[mapping];
        })), 'model_singular'), function (mapping) {
        return mapping.model_singular && mapping.title_singular;
      });
      if (!this.attr('criteria.objectName')) {
        this.attr('criteria.objectName', _.first(types).model_singular);
      }

      return types;
    },
    title: function () {
      if (this.attr('root')) {
        return 'Mapped To';
      }
      return 'Where ' +
              CMS.Models[this.attr('modelName')].title_singular +
              ' is mapped to';
    },
    remove: function () {
      this.dispatch('remove');
    },
    addRelevant: function () {
      this.attr('criteria.mappedTo',
        GGRC.Utils.AdvancedSearch.create.mappingCriteria());
    },
    removeRelevant: function () {
      this.removeAttr('criteria.mappedTo');
    }
  });

  GGRC.Components('advancedSearchMappingCriteria', {
    tag: 'advanced-search-mapping-criteria',
    template: template,
    viewModel: viewModel,
    leakScope: false
  });
})(window.can, window.GGRC);

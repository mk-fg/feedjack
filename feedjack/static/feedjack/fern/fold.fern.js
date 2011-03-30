(function() {
  /*
  // TODO: localStorage cleanup, check it's space limits
  // TODO: jquery.ui animation
  // TODO: fix style for links (bg crap on hover)
  // TODO: unfold button
  */  $(document).ready(function() {
    /* IE6? Fuck off */;    var fold_entries, folds, folds_commit, storage_key, url_media, url_site, _ref;
    if (typeof localStorage == "undefined" || localStorage === null) {
      return;
    }
    _ref = [$('html').data('url_site'), $('html').data('url_media')], url_site = _ref[0], url_media = _ref[1];
    storage_key = "feedjack.fold." + url_site;
    folds = localStorage.getItem(storage_key);
    folds = folds ? JSON.parse(folds) : {};
    folds_commit = function() {
      return localStorage.setItem(storage_key, JSON.stringify(folds));
    };
    /* Fold everything under the specified day-header */;
    fold_entries = function(h1, fold) {
      var ts_day, ts_entry_max;
      if (fold == null) {
        fold = null;
      }
      h1 = $(h1);
      ts_day = h1.data('timestamp');
      ts_entry_max = 0;
      h1.nextUntil('h1').children('.entry').each(function(idx, el) {
        var entry, ts;
        entry = $(el);
        ts = entry.data('timestamp');
        if (fold === false) {
          entry.children('.content').css('display', '');
        } else if (folds[ts_day] >= ts) {
          entry.children('.content').css('display', 'none');
        }
        if ((!(folds[ts_day] != null) || folds[ts_day] < ts) && ts > ts_entry_max) {
          return ts_entry_max = ts;
        }
      });
      /* No newer entries for a given day */;
      if (fold !== false && (fold || ts_entry_max === 0)) {
        h1.nextUntil('h1').css('display', 'none');
      }
      return [ts_day, ts_entry_max];
    };
    /* Buttons, initial fold */;
    $('h1.feed').append("<img title=\"fold everything\" class=\"button_fold_all\" src=\"" + url_media + "/fold_all.png\" />\n<img title=\"fold day\" class=\"button_fold\" src=\"" + url_media + "/fold.png\" />").each(function(idx, el) {
      return fold_entries(el);
    });
    /* Fold day */;
    $('.button_fold').click(function(ev) {
      var ts_day, ts_entry_max, _ref;
      _ref = fold_entries($(ev.target).parent('h1'), true), ts_day = _ref[0], ts_entry_max = _ref[1];
      folds[ts_day] = Math.max(ts_entry_max, folds[ts_day] || 0);
      return folds_commit();
    });
    /* Fold all */;
    return $('.button_fold_all').click(function(ev) {
      return $('h1.feed').each(function(idx, el) {
        var ts_day, ts_entry_max, _ref;
        _ref = fold_entries(el, true), ts_day = _ref[0], ts_entry_max = _ref[1];
        folds[ts_day] = Math.max(ts_entry_max, folds[ts_day] || 0);
        return folds_commit();
      });
    });
  });
}).call(this);

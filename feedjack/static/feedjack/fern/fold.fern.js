(function() {
  var __hasProp = Object.prototype.hasOwnProperty;
  $(document).ready(function() {
    /* IE6? Fuck off */;
    var fold_css, fold_entries, folds, folds_commit, folds_lru, folds_sync, folds_ts, folds_update, get_ts, img_sync, limit, limit_lru, limit_lru_gc, site_key, storage_key, url_media, url_site, url_store, _ref, _ref2, _ref3;
    if (typeof localStorage === "undefined" || localStorage === null) {
      return;
    }
    /* size of lru journal to trigger gc */;
    limit_lru_gc = 300;
    /* size of lru journal after cleanup */;
    limit_lru = 200;
    /* minimum number of folds to keep */;
    limit = 100;
    /* css class to mark folded entries with */;
    fold_css = 'folded';
    Object.prototype.get_length = function() {
      var k, len, v;
      len = 0;
      for (k in this) {
        if (!__hasProp.call(this, k)) continue;
        v = this[k];
        len += 1;
      }
      return len;
    };
    get_ts = function() {
      return Math.round((new Date()).getTime() / 1000);
    };
    _ref = [$('html').data('url_site'), $('html').data('url_media'), $('html').data('url_store')], url_site = _ref[0], url_media = _ref[1], url_store = _ref[2];
    site_key = url_site;
    storage_key = "feedjack.fold." + site_key;
    _ref2 = [localStorage["" + storage_key + ".folds"], localStorage["" + storage_key + ".folds_lru"], localStorage["" + storage_key + ".folds_ts"]], folds = _ref2[0], folds_lru = _ref2[1], folds_ts = _ref2[2];
    _ref3 = [folds ? JSON.parse(folds) : {}, folds_lru ? JSON.parse(folds_lru) : [], folds_ts ? JSON.parse(folds_ts) : {}], folds = _ref3[0], folds_lru = _ref3[1], folds_ts = _ref3[2];
    folds_update = function(key, value) {
      if (value == null) {
        value = 0;
      }
      folds[key] = value;
      folds_lru.push([key, value]);
      return folds_ts[key] = get_ts();
    };
    folds_commit = function() {
      /* gc */;
      var folds_lru_gc, key, len_folds, len_lru, val, _i, _len, _ref4, _ref5;
      len_lru = folds_lru.length;
      if (len_lru > limit_lru_gc) {
        _ref4 = [folds_lru.slice(len_lru - limit_lru, (len_lru + 1) || 9e9), folds_lru.slice(0, len_lru - limit_lru)], folds_lru = _ref4[0], folds_lru_gc = _ref4[1];
        len_folds = folds.get_length() - limit;
        for (_i = 0, _len = folds_lru_gc.length; _i < _len; _i++) {
          _ref5 = folds_lru_gc[_i], key = _ref5[0], val = _ref5[1];
          if (len_folds <= 0) {
            break;
          }
          if (folds[key] === val) {
            folds_update(key);
            len_folds -= 1;
          }
        }
      }
      /* actual storage */;
      localStorage["" + storage_key + ".folds"] = JSON.stringify(folds);
      localStorage["" + storage_key + ".folds_lru"] = JSON.stringify(folds_lru);
      return localStorage["" + storage_key + ".folds_ts"] = JSON.stringify(folds_ts);
    };
    folds_sync = function(ev) {
      var img, timer;
      if (!$.cookie('feedjack.tracking')) {
        return;
      }
      /* rotation effect for image while data ping-pong goes on */;
      img = $(ev.target);
      timer = setInterval((function() {
        var tilt;
        tilt = img.data('tilt') || 0;
        img.css({
          'transform': "rotate(" + tilt + "deg)",
          '-moz-transform': "rotate(" + tilt + "deg)",
          '-o-transform': "rotate(" + tilt + "deg)",
          '-webkit-transform': "rotate(" + tilt + "deg)"
        });
        return img.data('tilt', tilt - 10);
      }), 80);
      return $.get(url_store, {
        site_key: site_key
      }, function(raw, status) {
        var data, k, v, _ref4;
        data = raw || {
          folds: {},
          folds_ts: {}
        };
        if (status !== 'success' || !data) {
          alert("Failed to fetch data (" + status + "): " + raw);
        }
        _ref4 = data.folds;
        for (k in _ref4) {
          if (!__hasProp.call(_ref4, k)) continue;
          v = _ref4[k];
          if (!(folds_ts[k] != null) || data.folds_ts[k] > folds_ts[k]) {
            folds_update(k, v);
          }
        }
        folds_commit();
        $('.day>h1').each(function(idx, el) {
          return fold_entries(el);
        });
        return $.post(url_store, JSON.stringify({
          site_key: site_key,
          folds: folds,
          folds_ts: folds_ts
        }), function(raw, status) {
          if (status !== 'success' || !JSON.parse(raw)) {
            alert("Failed to send data (" + status + "): " + raw);
          }
          return clearInterval(timer);
        });
      });
    };
    /* (un)fold everything under the specified day-header */;
    fold_entries = function(h1, fold, unfold) {
      var ts_day, ts_entry_max;
      if (fold == null) {
        fold = null;
      }
      if (unfold == null) {
        unfold = false;
      }
      h1 = $(h1);
      ts_day = h1.data('timestamp');
      ts_entry_max = 0;
      /* (un)fold channel */;
      h1.nextAll('.channel').each(function(idx, el) {
        var channel, fold_channel;
        channel = $(el);
        fold_channel = true;
        /* (un)fold entries */;
        channel.children('.entry').each(function(idx, el) {
          var entry, fold_entry, ts;
          entry = $(el);
          ts = entry.data('timestamp');
          fold_entry = false;
          if (unfold === true || !(folds[ts_day] != null)) {
            entry.removeClass(fold_css);
          } else if (fold !== false && folds[ts_day] >= ts) {
            entry.addClass(fold_css);
            fold_entry = true;
          }
          if (!fold_entry) {
            fold_channel = false;
            if (ts > ts_entry_max) {
              return ts_entry_max = ts;
            }
          }
        });
        if (fold_channel) {
          return channel.addClass(fold_css);
        } else {
          return channel.removeClass(fold_css);
        }
      });
      /* (un)fold whole day */;
      if (unfold === true) {
        h1.parent().removeClass(fold_css);
      } else if (fold !== false && (fold || ts_entry_max === 0)) {
        h1.parent().addClass(fold_css);
      }
      return [ts_day, ts_entry_max];
    };
    /* Buttons, initial fold */;
    img_sync = $.cookie('feedjack.tracking') ? "<img title=\"fold sync\" class=\"button_fold_sync\" src=\"" + url_media + "/fold_sync.png\" />" : '';
    $('.day>h1').append(("<img title=\"fold page\" class=\"button_fold_all\" src=\"" + url_media + "/fold_all.png\" />\n<img title=\"fold day\" class=\"button_fold\" src=\"" + url_media + "/fold.png\" />") + img_sync).each(function(idx, el) {
      return fold_entries(el);
    });
    /* Fold sync button */;
    $('.button_fold_sync').click(folds_sync);
    /* Fold day button */;
    $('.button_fold').click(function(ev) {
      var h1, ts_day, ts_entry_max, _ref4;
      h1 = $(ev.target).parent('h1');
      _ref4 = fold_entries(h1, false), ts_day = _ref4[0], ts_entry_max = _ref4[1];
      if (ts_entry_max > 0) {
        fold_entries(h1, true);
        folds_update(ts_day, Math.max(ts_entry_max, folds[ts_day] || 0));
      } else {
        fold_entries(h1, false, true);
        folds_update(ts_day);
      }
      return folds_commit();
    });
    /* Fold all button */;
    return $('.button_fold_all').click(function(ev) {
      var h1s, ts_page_max;
      ts_page_max = 0;
      h1s = $('.day>h1');
      h1s.each(function(idx, el) {
        return ts_page_max = Math.max(ts_page_max, fold_entries(el, false)[1]);
      });
      if (ts_page_max > 0) {
        h1s.each(function(idx, el) {
          var ts_day, ts_entry_max, _ref4;
          _ref4 = fold_entries(el, true), ts_day = _ref4[0], ts_entry_max = _ref4[1];
          return folds_update(ts_day, Math.max(ts_entry_max, folds[ts_day] || 0));
        });
      } else {
        h1s.each(function(idx, el) {
          var ts_day, ts_entry_max, _ref4;
          _ref4 = fold_entries(el, false, true), ts_day = _ref4[0], ts_entry_max = _ref4[1];
          return folds_update(ts_day);
        });
      }
      return folds_commit();
    });
  });
}).call(this);

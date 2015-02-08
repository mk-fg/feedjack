$(document).ready ->
	# IE6? Fuck off
	return unless localStorage?

	# size of lru journal to trigger gc
	limit_lru_gc = 300
	# size of lru journal after cleanup
	limit_lru = 200
	# minimum number of folds to keep
	limit = 100
	# css class to mark folded entries with
	fold_css = 'folded'

	get_length = (obj) ->
		len = 0
		len += 1 for own k,v of obj
		len

	get_ts = -> Math.round((new Date()).getTime() / 1000)

	[url_site, url_static] = [
		$('html').data('url_site'),
		$('html').data('url_static') ]
	site_key = url_site
	storage_key = "feedjack.fold.#{site_key}"
	[folds, folds_lru, folds_ts] = [
		localStorage["#{storage_key}.folds"],
		localStorage["#{storage_key}.folds_lru"],
		localStorage["#{storage_key}.folds_ts"] ]
	[folds, folds_lru, folds_ts] = [
		if folds then JSON.parse(folds) else {},
		if folds_lru then JSON.parse(folds_lru) else [],
		if folds_ts then JSON.parse(folds_ts) else {} ]

	folds_update = (key, value=0) ->
		folds[key] = value
		folds_lru.push([key, value])
		folds_ts[key] = get_ts()

	folds_commit = ->
		# gc
		len_lru = folds_lru.length
		if len_lru > limit_lru_gc
			[folds_lru, folds_lru_gc] = [
				folds_lru[(len_lru - limit_lru)..len_lru],
				folds_lru[0...(len_lru - limit_lru)] ]
			len_folds = get_length(folds) - limit
			for [key,val] in folds_lru_gc
				break if len_folds <= 0
				if folds[key] == val
					folds_update(key)
					len_folds -= 1
		# actual storage
		localStorage["#{storage_key}.folds"] = JSON.stringify(folds)
		localStorage["#{storage_key}.folds_lru"] = JSON.stringify(folds_lru)
		localStorage["#{storage_key}.folds_ts"] = JSON.stringify(folds_ts)

	# (un)fold everything under the specified day-header
	fold_entries = (h1, fold=null, unfold=false) ->
		try
			_fold_entries(h1, fold, unfold)
		catch err
			console.log(err)

	_fold_entries = (h1, fold=null, unfold=false) ->
		h1 = $(h1)
		ts_day = h1.data('timestamp')
		ts_entry_max = 0

		# (un)fold channel
		h1.nextAll('.channel').each (idx, el) ->
			channel = $(el)
			fold_channel = true

			# (un)fold entries
			entries = channel.find('.entry')
			if not entries.length
				fold_channel = false
				ts_entry_max = 1 # make sure whole day won't be folded
			else
				entries.each (idx, el) ->
					entry = $(el)
					ts = entry.data('timestamp')
					if not ts # make this item unfoldable
						ts_entry_max = 1
						return
					fold_entry = false
					fold_ts_day = folds[ts_day]
					if unfold is true or not fold_ts_day?
						entry.removeClass(fold_css)
					else if fold_ts_day >= ts
						if fold isnt false
							entry.addClass(fold_css)
							links_entry = entry.find('a')
							links_entry_unfold = ->
								entry.removeClass(fold_css)
								links_entry.unbind('click', links_entry_unfold)
								false
							links_entry.click(links_entry_unfold)
						fold_entry = true
					if not fold_entry
						fold_channel = false
						ts_entry_max = ts if ts > ts_entry_max

			if fold_channel
				channel.addClass(fold_css)
				links_channel = channel.find('a')
				links_channel_unfold = ->
					channel.removeClass(fold_css)
					links_channel.unbind('click', links_channel_unfold)
					false
				links_channel.click(links_channel_unfold)
			else
				channel.removeClass(fold_css)

		# (un)fold whole day
		if unfold is true
			h1.parent().removeClass(fold_css)
		else if fold isnt false and (fold or ts_entry_max == 0)
			h1.parent().addClass(fold_css)

		[ts_day, ts_entry_max]

	# Buttons, initial fold
	$('.day>h1')
		.append(
			"""<img title="fold page" class="button_fold_all" src="#{url_static}/fold_all.png" />
			<img title="fold day" class="button_fold" src="#{url_static}/fold.png" />""" ) #"
		.each (idx, el) -> fold_entries(el)

	# Fold day button
	$('.button_fold').click (ev) ->
		h1 = $(ev.target).parent('h1')
		# Check whether stuff needs to be folded or unfolded
		[ts_day, ts_entry_max] = fold_entries(h1, false)
		if ts_entry_max > 0
			# Fold
			fold_entries(h1, true)
			folds_update(ts_day, Math.max(ts_entry_max, folds[ts_day] or 0))
		else
			# Unfold
			fold_entries(h1, false, true)
			folds_update(ts_day)
		folds_commit()

	# Fold all button
	$('.button_fold_all').click (ev) ->
		ts_page_max = 0
		h1s = $('.day>h1')
		h1s.each (idx, el) ->
			ts_page_max = Math.max(ts_page_max, fold_entries(el, false)[1])
		if ts_page_max > 0
			h1s.each (idx, el) ->
				[ts_day, ts_entry_max] = fold_entries(el, true)
				folds_update(ts_day, Math.max(ts_entry_max, folds[ts_day] or 0))
		else
			h1s.each (idx, el) ->
				[ts_day, ts_entry_max] = fold_entries(el, false, true)
				folds_update(ts_day)
		folds_commit()


# Prefix for values in localStorage
localStorage_prefix = $('script').last().data('localStorage_prefix')

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

	Object::get_length = ->
		len = 0
		len += 1 for own k,v of this
		len

	get_ts = -> Math.round((new Date()).getTime() / 1000)

	[folds, folds_lru, folds_ts] = [
		localStorage["#{localStorage_prefix}.folds"],
		localStorage["#{localStorage_prefix}.folds_lru"],
		localStorage["#{localStorage_prefix}.folds_ts"] ]
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
			len_folds = folds.get_length() - limit
			for [key,val] in folds_lru_gc
				break if len_folds <= 0
				if folds[key] == val
					folds_update(key)
					len_folds -= 1
		# actual storage
		localStorage["#{localStorage_prefix}.folds"] = JSON.stringify(folds)
		localStorage["#{localStorage_prefix}.folds_lru"] = JSON.stringify(folds_lru)
		localStorage["#{localStorage_prefix}.folds_ts"] = JSON.stringify(folds_ts)

	# (un)fold everything under the specified day-header
	fold_entries = (day, fold=null, unfold=false) ->
		ts_day = day.data('timestamp')
		ts_entry_max = 0

		# (un)fold channel
		day.find('.channel').each ->
			channel = $(this)
			fold_channel = true

			# (un)fold entries
			entries = channel.find('.entry')
			if not entries.length
				fold_channel = false
				ts_entry_max = 1 # make sure whole day won't be folded
			else
				entries.each ->
					entry = $(this)
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
			day.removeClass(fold_css)
		else if fold isnt false and (fold or ts_entry_max == 0)
			day.addClass(fold_css)

		[ts_day, ts_entry_max]

	fold_apply = (fold_btn, toggle=true) ->
		fold_btn = $(fold_btn)
		day = fold_btn.parents('.day')
		# Check whether stuff needs to be folded or unfolded
		[ts_day, ts_entry_max] = fold_entries(day, false)
		if (ts_entry_max == 0) ^ toggle
			# Fold
			fold_entries(day, true)
			folds_update(ts_day, Math.max(ts_entry_max, folds[ts_day] or 0))
			fold_btn.children('i').attr('class', 'icon-plus')
		else
			# Unfold
			fold_entries(day, false, true)
			folds_update(ts_day)
			fold_btn.children('i').attr('class', 'icon-minus')
		if toggle
			folds_commit()

	# Fold day buttons
	$('.fold-toggle').click (ev) ->
		fold_apply($(ev.target).parents('.fold-toggle').andSelf())

	# Initial (un)fold, show controls
	$('.fold-controls').each ->
		$(this).show().find('.fold-toggle').each ->
			fold_btn = $(this)
			[ts_day, ts_entry_max] = fold_entries(fold_btn.parents('.day'))
			fold_btn.children('i').attr( 'class',
				if ts_entry_max == 0 then 'icon-plus' else 'icon-minus' )

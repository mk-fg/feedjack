
# site_key is used to prefix values in storage api's
site_key = $('script').last().data('site_key')
localStorage_prefix = "feedjack.#{site_key}.fold"

# Listen for storage-ready event
storage = null
$(document).on( 'fold_storage_init', (ev, storage_obj) ->
	storage = storage_obj
	$('.btn.fold-sync').show() )


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
		len += 1 for own k,v of this
		return len

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
		# GC
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
		# Actual storage
		localStorage["#{localStorage_prefix}.folds"] = JSON.stringify(folds)
		localStorage["#{localStorage_prefix}.folds_lru"] = JSON.stringify(folds_lru)
		localStorage["#{localStorage_prefix}.folds_ts"] = JSON.stringify(folds_ts)


	folds_sync = (ev) ->
		# Get storage object
		if not storage?
			alert('Unable to remote storage api.')
			return
		# "In progress" effect for button
		btn = $(ev.target).parents('.btn').andSelf().filter('.btn')
		btn.button('loading')
		# Actual storage sync
		storage.get site_key, (error, data) ->
			if error and error != 404
				# alert("Failed to fetch data from storage: #{error} (data: #{data})")
				return btn.button('reset')
			data = JSON.parse(data or "null") or {folds: {}, folds_ts: {}}
			for own k,v of data.folds
				folds_update(k, v) if not folds_ts[k]? or data.folds_ts[k] > folds_ts[k]
			folds_commit()
			$('.fold-controls .fold-toggle').each -> fold_apply(this)
			storage.put site_key, JSON.stringify({site_key, folds, folds_ts}), (error) ->
				# if error
				# 	alert("Failed to store data: #{error}")
				btn.button('reset')

	$('.btn.fold-sync').on('click', folds_sync)


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
							links_entry.on('click', links_entry_unfold)
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
				links_channel.on('click', links_channel_unfold)
			else
				channel.removeClass(fold_css)

		# (un)fold whole day
		if unfold is true
			day.removeClass(fold_css)
		else if fold isnt false and (fold or ts_entry_max == 0)
			day.addClass(fold_css)

		[ts_day, ts_entry_max]

	# Fold day button triggers
	$('.fold-toggle').click (ev, toggle=true) ->
		fold_btn = $(ev.target).parents('.fold-toggle').andSelf()
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

	# Initial (un)fold, show controls
	fold_apply = (fold_btn) ->
		fold_btn = $(fold_btn)
		[ts_day, ts_entry_max] = fold_entries(fold_btn.parents('.day'))
		fold_btn.children('i').attr( 'class',
			if ts_entry_max == 0 then 'icon-plus' else 'icon-minus' )

	$('.fold-controls').each ->
		$(this).show().find('.fold-toggle').each -> fold_apply(this)

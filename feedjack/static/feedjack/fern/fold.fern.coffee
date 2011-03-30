###
// TODO: localStorage cleanup, check it's space limits
// TODO: jquery.ui animation
// TODO: fix style for links (bg crap on hover)
// TODO: unfold button
###

$(document).ready ->
	/* IE6? Fuck off */
	return unless localStorage?

	[url_site, url_media] = [$('html').data('url_site'), $('html').data('url_media')]
	storage_key = "feedjack.fold.#{url_site}"
	folds = localStorage.getItem(storage_key)
	folds = if folds then JSON.parse(folds) else {}
	folds_commit = -> localStorage.setItem(storage_key, JSON.stringify(folds))

	/* Fold everything under the specified day-header */
	fold_entries = (h1, fold=null) ->
		h1 = $(h1)
		ts_day = h1.data('timestamp')
		ts_entry_max = 0

		h1.nextUntil('h1').children('.entry').each (idx, el) ->
			entry = $(el)
			ts = entry.data('timestamp')
			if fold is false
				entry.children('.content').css('display', '')
			else if folds[ts_day] >= ts
				entry.children('.content').css('display', 'none')
			ts_entry_max = ts if (not folds[ts_day]? or folds[ts_day] < ts) and ts > ts_entry_max

		/* No newer entries for a given day */
		if fold isnt false and (fold or ts_entry_max == 0)
			h1.nextUntil('h1').css('display', 'none')

		[ts_day, ts_entry_max]

	/* Buttons, initial fold */
	$('h1.feed')
		.append(
			"""<img title="fold everything" class="button_fold_all" src="#{url_media}/fold_all.png" />
			<img title="fold day" class="button_fold" src="#{url_media}/fold.png" />""" )
		.each (idx, el) -> fold_entries(el)

	/* Fold day */
	$('.button_fold').click (ev) ->
		[ts_day, ts_entry_max] = fold_entries($(ev.target).parent('h1'), true)
		folds[ts_day] = Math.max(ts_entry_max, folds[ts_day] or 0)
		folds_commit()

	/* Fold all */
	$('.button_fold_all').click (ev) ->
		$('h1.feed').each (idx, el) ->
			[ts_day, ts_entry_max] = fold_entries(el, true)
			folds[ts_day] = Math.max(ts_entry_max, folds[ts_day] or 0)
			folds_commit()

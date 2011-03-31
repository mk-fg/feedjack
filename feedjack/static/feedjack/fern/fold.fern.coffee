###
// TODO: localStorage cleanup, check it's space limits
// TODO: jquery.ui animation
// TODO: fix style for links (bg crap on hover)
###

$(document).ready ->
	/* IE6? Fuck off */
	return unless localStorage?

	[url_site, url_media] = [$('html').data('url_site'), $('html').data('url_media')]
	storage_key = "feedjack.fold.#{url_site}"
	folds = localStorage.getItem(storage_key)
	folds = if folds then JSON.parse(folds) else {}
	folds_commit = -> localStorage.setItem(storage_key, JSON.stringify(folds))

	/* (un)fold everything under the specified day-header */
	fold_entries = (h1, fold=null, unfold=false) ->
		h1 = $(h1)
		ts_day = h1.data('timestamp')
		ts_entry_max = 0

		/* (un)fold entries */
		h1.nextUntil('h1').children('.entry').each (idx, el) ->
			entry = $(el)
			ts = entry.data('timestamp')
			if unfold is true
				entry.children('.content').css('display', '')
			else if fold isnt false and folds[ts_day] >= ts
				entry.children('.content').css('display', 'none')
			ts_entry_max = ts if (not folds[ts_day]? or folds[ts_day] < ts) and ts > ts_entry_max

		/* (un)fold whole day */
		if unfold is true
			h1.nextUntil('h1').css('display', '')
		else if fold isnt false and (fold or ts_entry_max == 0)
			h1.nextUntil('h1').css('display', 'none')

		[ts_day, ts_entry_max]

	/* Buttons, initial fold */
	$('h1.feed')
		.append(
			"""<img title="fold page" class="button_fold_all" src="#{url_media}/fold_all.png" />
			<img title="fold day" class="button_fold" src="#{url_media}/fold.png" />""" )
		.each (idx, el) -> fold_entries(el)

	/* Fold day button */
	$('.button_fold').click (ev) ->
		h1 = $(ev.target).parent('h1')
		[ts_day, ts_entry_max] = fold_entries(h1, false)
		if ts_entry_max > 0
			fold_entries(h1, true)
			folds[ts_day] = Math.max(ts_entry_max, folds[ts_day] or 0)
		else
			fold_entries(h1, false, true)
			delete folds[ts_day]
		folds_commit()

	/* Fold all button */
	$('.button_fold_all').click (ev) ->
		ts_page_max = 0
		h1s = $('h1.feed')
		h1s.each (idx, el) ->
			ts_page_max = Math.max(ts_page_max, fold_entries(el, false)[1])
		if ts_page_max > 0
			h1s.each (idx, el) ->
				[ts_day, ts_entry_max] = fold_entries(el, true)
				folds[ts_day] = Math.max(ts_entry_max, folds[ts_day] or 0)
		else
			h1s.each (idx, el) ->
				[ts_day, ts_entry_max] = fold_entries(el, false, true)
				delete folds[ts_day]
		folds_commit()

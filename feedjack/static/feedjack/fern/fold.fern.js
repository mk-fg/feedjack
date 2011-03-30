$(document).ready(function() {
	var url_fold = $('html').data('url_ajax_fold')
	var url_media = $('html').data('url_media')

	$('h1.feed').append(
		'<img class="button_fold_all" src="'+url_media+'/fold_all.png" />'
		+ '<img class="button_fold" src="'+url_media+'/fold.png" />' )

	$('.button_fold').click(function(ev) {
		var h1 = $(ev.target).parent('h1')
		var ts_day = h1.data('timestamp')
		var ts_entry_max = 0

		h1.nextUntil('h1').children('.entry')
			.each(function(idx, el) {
				var ts = $(el).data('timestamp')
				if (ts > ts_entry_max) ts_entry_max = ts })

		// TODO: client-side storage
		// $.getJSON( url_fold,
		// 	{ts_day: ts_day, ts_entry_max: ts_entry_max},
		// 	function(data) {
		// 		// TODO: actually fold the thing
		// 		// TODO: jquery.ui animation
		// 		// TODO: fix style for links (bg crap on hover)
		// 		// alert(data)
		// 		} ) })
})

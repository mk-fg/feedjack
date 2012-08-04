
script = $('script').last()
# site_key is used to prefix values in storage api's
site_key = $('script').last().data('site_key')
localStorage_prefix = "feedjack.#{site_key}.rs"
storage_category = "feedjack.fold"
# Callback URL with JS to get access_token from fragment
receive_token_url = script.data('receive_token_url')


$(document).ready ->
	rs_form = $('#rs-form')

	# Necessary to stop form from disappearing on click
	rs_form.click (ev) ->
		ev.stopPropagation()

	if not receive_token_url?
		console.log( 'Failed to find receive_token'
			+ ' interface URL, remoteStorage interface will be disabled.' )
		rs_form.find('input, .btn').addClass('disabled').attr('disabled', 'disabled')
		return


	# --- Storage API wrapper

	class Storage
		@auth_callback = null

		constructor: (@category) ->
			# Listener for authorization events
			$(window).on( 'message', (ev) =>
				ev = ev.originalEvent
				if ev.origin == location.protocol+'//'+location.host
					console.log('Received an OAuth token: ' + ev.data)
					localStorage.setItem("#{localStorage_prefix}.bearerToken", ev.data)
					if @auth_callback?
						@auth_callback() )

		connect: (user_address, callback) ->
			# Takes a user address ("user@host") and a callback as its arguments.
			# The callback will get an error code, and a `storageInfo` object.
			remoteStorage.getStorageInfo( user_address, (error, storageInfo) ->
				if error
					alert('Could not load storage info')
					console.log(error)
				else
					console.log('Storage info received:')
					console.log(storageInfo)
				callback(error, storageInfo) )

		authorize: (scopes, callback) ->
			# Opens a popup that sends the user to the OAuth dialog of the remoteStorage provider.
			scopes ?= [@category + ':rw']
			storageInfo = JSON.parse \
				localStorage.getItem("#{localStorage_prefix}.userStorageInfo")
			redirectUri = location.protocol + '//' + location.host + receive_token_url
			@auth_callback = callback
			window.open \
				remoteStorage.createOAuthAddress(storageInfo, scopes, redirectUri)

		get: (key, callback) ->
			storageInfo = JSON.parse \
				localStorage.getItem("#{localStorage_prefix}.userStorageInfo")
			token = localStorage.getItem("#{localStorage_prefix}.bearerToken")
			if not storageInfo? or not token?
				alert('No remoteStorage authorization, please connect/authorize first.')
				return callback(401)
			path = @category + '/' + key
			client = remoteStorage.createClient(storageInfo, '', token)

			client.get( path, (error, data) ->
				if error == 401
					alert('Your session has expired. Please connect to your remoteStorage again.')
				else
					if error
						alert('Could not find "' + path + '" on the remoteStorage')
						console.log(error)
					else
						if not data?
							console.log('There wasn\'t anything for "' + path + '"')
						else
							console.log('Received item "' + path + '": ' + data)
				callback(error, data) )

		put: (key, value, callback) ->
			# Takes a key, the value and a callback.
			storageInfo = JSON.parse \
				localStorage.getItem("#{localStorage_prefix}.userStorageInfo")
			path = @category + '/' + key
			token = localStorage.getItem("#{localStorage_prefix}.bearerToken")
			client = remoteStorage.createClient(storageInfo, '', token)

			client.put( path, value, (error) ->
				if error == 401
					alert('Your session has expired. Please connect to your remoteStorage again.')
				else
					if error
						alert('Could not store "' + path + '"')
						console.log(error)
					else
						console.log('Stored "' + value + '" for item "' + path + '"')
				callback(error) )

	storage = new Storage(storage_category)
	$(document).trigger('fold_storage_init', storage)


	# --- Storage Interface

	connected = localStorage.getItem(
		"#{localStorage_prefix}.userStorageInfo" ) != null
	authorized = localStorage.getItem(
		"#{localStorage_prefix}.bearerToken" ) != null

	state_update_hook = ->
		# Connection state
		if connected
			# Set userAddress in a form to the one stored
			rs_form.find('input[name="userAddress"]').val \
				localStorage.getItem("#{localStorage_prefix}.userAddress")
			rs_form.find('.btn.connect').addClass('btn-success')
		else
			rs_form.find('.btn.connect').removeClass('btn-success')
		if authorized
			rs_form.find('.btn.authorize').addClass('btn-success')
		else
			rs_form.find('.btn.authorize').removeClass('btn-success')
	state_update_hook()

	connect_handler = (ev) ->
		if not connected
			user_address = rs_form.find('input[name="userAddress"]').val()
			storage.connect( user_address, (error, storageInfo) ->
				if error
					connected = false
				else
					localStorage.setItem \
						"#{localStorage_prefix}.userStorageInfo", JSON.stringify(storageInfo)
					localStorage.setItem \
						"#{localStorage_prefix}.userAddress", user_address
					connected = true
				state_update_hook() )
		else
			localStorage.removeItem("#{localStorage_prefix}.userStorageInfo")
			localStorage.removeItem("#{localStorage_prefix}.bearerToken")
			connected = authorized = false
			state_update_hook()
			connect_handler(ev)
		return false
	rs_form.find('.connect').on('click', connect_handler)

	rs_form.find('.authorize').on( 'click', ->
		if not authorized
			storage.authorize( null, ->
				authorized = true
				state_update_hook() )
		else
			localStorage.removeItem("#{localStorage_prefix}.bearerToken")
			authorized = false
			state_update_hook()
		return false )

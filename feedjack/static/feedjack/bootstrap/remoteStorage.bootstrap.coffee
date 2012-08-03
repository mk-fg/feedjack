
script = $('script').last()
# Prefix for values in localStorage
localStorage_prefix = script.data('localStorage_prefix')
# Callback URL with JS to get access_token from fragment
receive_token_url = script.data('receive_token_url')

$(document).ready ->
	rs_form = $('#rs-form')

	# Necessary to stop form from disappearing on click
	rs_form.click (ev) ->
		ev.stopPropagation()

	# TODO: some msg in this case
	# if (receive_token_url == undefined) return;


	# --- Storage API wrapper

	storage = do ->

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
			storageInfo = JSON.parse(localStorage.getItem('userStorageInfo'))
			redirectUri = location.protocol + '//' + location.host + receive_token_url

			window.addEventListener(
				'message', (event) ->
					if event.origin == location.protocol + '//' + location.host
						console.log('Received an OAuth token: ' + event.data)
						localStorage.setItem('bearerToken', event.data)
						callback()
				, false )

			window.open \
				remoteStorage.createOAuthAddress(storageInfo, scopes, redirectUri)

		getData: (path, callback) ->
			# Takes the object that from connect call and the category to access.
			# If the category is any other than "public", OAuth token should be in localStorage.
			storageInfo = JSON.parse(localStorage.getItem('userStorageInfo'))

			if path.split('/').length < 2
				cb('error: path '+path+' contains no slashes');
				return
			else
				if path.split('/')[0] == 'public'
					client = remoteStorage.createClient(storageInfo, '')
				else
					token = localStorage.getItem('bearerToken')
					client = remoteStorage.createClient(storageInfo, '', token)

			client.get( path, (error, data) ->
				if error==401
					alert('Your session has expired. Please connect to your remoteStorage again.')
				else
					if error
						alert('Could not find "' + path + '" on the remoteStorage')
						console.log(error)
					else
						if data == undefined
							console.log('There wasn\'t anything for "' + path + '"')
						else
							console.log('We received this for item "' + path + '": ' + data)
				callback(error, data) )

		putData: (path, value, callback) ->
			# Takes a key, the value and a callback.
			storageInfo = JSON.parse(localStorage.getItem('userStorageInfo'))
			token = localStorage.getItem('bearerToken')
			client = remoteStorage.createClient(storageInfo, '', token)

			client.put \
					path, value, (error) ->
				if error == 401
					alert('Your session has expired. Please connect to your remoteStorage again.')
				else
					if error
						alert('Could not store "' + path + '"')
						console.log(error)
					else
						console.log('Stored "' + value + '" for item "' + path + '"')

				callback(error)


	# --- Storage Interface

	connected = localStorage.getItem('userStorageInfo') != null
	authorized = localStorage.getItem('bearerToken') != null

	state_update_hook = ->
		# Connection state
		[show, hide] = if connected\
			then ['connected', 'disconnected']\
			else ['disconnected', 'connected']
		rs_form.find("span.#{hide}").hide()
		rs_form.find("span.#{show}").show()
		# Authorization state
		[show, hide] = if authorized\
			then ['authorized', 'unauthorized']\
			else ['unauthorized', 'authorized']
		rs_form.find("span.#{hide}").hide()
		rs_form.find("span.#{show}").show()
	state_update_hook()

	connect_handler = (ev) ->
		if not connected
			user_address = rs_form.find('input[name="userAddress"]').val()
			storage.connect( user_address, (error, storageInfo) ->
				if error
					connected = false
				else
					localStorage.setItem('userStorageInfo', JSON.stringify(storageInfo))
					localStorage.setItem('userAddress', user_address)
					connected = true
				state_update_hook() )
		else
			localStorage.removeItem('userStorageInfo')
			localStorage.removeItem('bearerToken')
			connected = authorized = false
			state_update_hook()
			connect_handler(ev)
		return false
	$('#connect').click(connect_handler)

	$('#authorize').click ->
		if not authorized
			storage.authorize( ['public/tutorial:rw', 'tutorial:rw'], ->
				authorized = true
				state_update_hook() )
		else
			localStorage.removeItem('bearerToken')
			authorized = false
			state_update_hook()
		return false

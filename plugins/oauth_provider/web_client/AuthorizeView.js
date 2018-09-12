import $ from 'jquery';
import _ from 'underscore';
import View from 'girder/views/View';
import { getCurrentUser, setCurrentToken, setCurrentUser } from 'girder/auth';
import { restRequest } from 'girder/rest';
import UserModel from 'girder/models/UserModel';

import consentTemplate from './consentTemplate.pug';
import loginTemplate from './loginTemplate.pug';
import './authorizeView.styl';


export default View.extend({
    events: {
        'click .g-oauth-client-consent': function (e) {
            restRequest({
                type: 'POST',
                url: `oauth_client/${this.client._id}/authorization`,
                data: {
                    authorize: $(e.currentTarget).attr('value'),
                    redirect: this.redirect,
                    scope: this.scopes.join(' '),
                    state: this.state
                }
            }).then((resp) => {
                window.location = resp.url;
            });
        },
        'submit .g-login-form': function (e) {
            e.preventDefault();
            this.$('.g-login-button').girderEnable(false);

            const username = this.$('#g-login').val();
            const password = this.$('#g-password').val();
            const auth = 'Basic ' + window.btoa(username + ':' + password);

            restRequest({
                url: '/user/authentication',
                headers: {'Girder-Authorization': auth},
                error: null
            }).then((response) => {
                setCurrentUser(new UserModel(response.user));
                setCurrentToken(response.authToken.token);
                this.mode = 'consent';
                this.render();
            }).fail((err) => {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
            }).always(() => {
                this.$('.g-login-button').girderEnable(true);
            });
        }
    },
    initialize(opts) {
        this.redirect = opts.redirect;
        this.state = opts.state;
        this.scopes = opts.scope.split(' ');

        const clientFetchXhr = restRequest({
            url: `/oauth_client/${opts.clientId}`
        }).then((resp) => resp);

        const scopeFetchXhr = restRequest({
            url: 'token/scopes'
        }).then((resp) => resp);

        $.when(clientFetchXhr, scopeFetchXhr).done((client, scopeInfo) => {
            this.client = client;
            this.scopeInfo = scopeInfo.custom.concat(scopeInfo.adminCustom || []);
            this.mode = getCurrentUser() ? 'consent' : 'login';
            this.render();
        });
    },

    render() {
        if (this.mode === 'consent') {
            this.$el.html(consentTemplate({
                client: this.client,
                getScopeInfo: this.getScopeInfo.bind(this),
                scopes: this.scopes,
                user: getCurrentUser(),
            }));
        } else if (this.mode === 'login') {
            this.$el.html(loginTemplate());
        }
        return this;
    },

    getScopeInfo(scopeId) {
        return _.find(this.scopeInfo, (info) => info.id === scopeId);
    }
});

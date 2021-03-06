import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils import translation
from django.conf import settings

from models import Agenda, AgendaVote
from knesset.laws.models import Vote, VoteAction
from knesset.mks.models import Party, Member
from knesset.committees.models import Committee, CommitteeMeeting
just_id = lambda x: x.id

class SimpleTest(TestCase):
    def setUp(self):
        self.party_1 = Party.objects.create(name='party 1')
        self.mk_1 = Member.objects.create(name='mk_1',
                                          start_date=datetime.date(2010,1,1),
                                          current_party=self.party_1)
        self.user_1 = User.objects.create_user('jacob', 'jacob@jacobian.org', 'JKM')
        self.user_2 = User.objects.create_user('john', 'lennon@thebeatles.com', 'LSD')
        self.user_3 = User.objects.create_user('superman', 'super@user.com', 'CRP')
        self.user_3.is_superuser = True
        self.user_3.save()

        self.agenda_1 = Agenda.objects.create(name='agenda 1',
                                              description='a bloody good agenda 1',
                                              public_owner_name='Dr. Jacob',
                                              is_public=True)
        self.agenda_2 = Agenda.objects.create(name='agenda 2',
                                              description='a bloody good agenda 2',
                                              public_owner_name='Greenpeace',
                                              is_public=True)
        self.agenda_3 = Agenda.objects.create(name='agenda 3',
                                              description='a bloody good agenda 3',
                                              public_owner_name='Hidden One',
                                              is_public=False)
        self.agenda_1.editors = [self.user_1]
        self.agenda_2.editors = [self.user_1, self.user_2]
        self.agenda_3.editors = [self.user_2]
        self.vote_1 = Vote.objects.create(title='vote 1',time=datetime.datetime.now())
        self.vote_2 = Vote.objects.create(title='vote 2',time=datetime.datetime.now())
        self.voteaction_1 = VoteAction.objects.create(vote=self.vote_1, member=self.mk_1, type='for')
        self.voteaction_2 = VoteAction.objects.create(vote=self.vote_2, member=self.mk_1, type='for')
        self.agendavote_1 = AgendaVote.objects.create(agenda=self.agenda_1,
                                                      vote=self.vote_1,
                                                      score=-1,
                                                      reasoning="there's got to be a reason 1")
        self.agendavote_2 = AgendaVote.objects.create(agenda=self.agenda_2,
                                                      vote=self.vote_2,
                                                      score=0.5,
                                                      reasoning="there's got to be a reason 2")
        self.agendavote_3 = AgendaVote.objects.create(agenda=self.agenda_1,
                                                      vote=self.vote_2,
                                                      score=0.5,
                                                      reasoning="there's got to be a reason 3")
        self.committee_1 = Committee.objects.create(name='c1')
        self.meeting_1 = self.committee_1.meetings.create(date=datetime.datetime.now(),
                                 protocol_text='''jacob:
I am a perfectionist
adrian:
I have a deadline''')
        self.meeting_1.create_protocol_parts()

        self.domain = 'http://' + Site.objects.get_current().domain

    def testAgendaList(self):
        translation.activate(settings.LANGUAGE_CODE)
        # test anonymous user
        res = self.client.get(reverse('agenda-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'agendas/agenda_list.html')
        object_list = res.context['object_list']
        self.assertEqual(map(just_id, object_list),
                         [ self.agenda_1.id, self.agenda_2.id, ])

        # test logged in user 1
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.get(reverse('agenda-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'agendas/agenda_list.html')
        object_list = res.context['object_list']
        self.assertEqual(map(just_id, object_list),
                         [ self.agenda_1.id, self.agenda_2.id, ])

        # test logged in user 2
        self.assertTrue(self.client.login(username='superman', password='CRP'))
        res = self.client.get(reverse('agenda-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'agendas/agenda_list.html')
        object_list = res.context['object_list']
        self.assertEqual(map(just_id, object_list),
                         [ self.agenda_1.id, self.agenda_2.id, self.agenda_3.id])

        # test logged in as superuser
        self.assertTrue(self.client.login(username='john', password='LSD'))
        res = self.client.get(reverse('agenda-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'agendas/agenda_list.html')
        object_list = res.context['object_list']
        self.assertEqual(map(just_id, object_list),
                         [ self.agenda_1.id, self.agenda_2.id, self.agenda_3.id])

        translation.deactivate()

    def testAgendaDetail(self):

        # Access public agenda while not logged in
        res = self.client.get(reverse('agenda-detail',
                                      kwargs={'pk': self.agenda_1.id}))
        self.assertTemplateUsed(res,
                                'agendas/agenda_detail.html')
        self.assertEqual(res.context['object'].id, self.agenda_1.id)
        self.assertEqual(res.context['object'].description, self.agenda_1.description)
        self.assertEqual(res.context['object'].public_owner_name, self.agenda_1.public_owner_name)
        self.assertEqual(list(res.context['object'].editors.all()), [self.user_1])

    def test_agenda_edit(self):

        # Try to edit agenda while not logged in
        res = self.client.get(reverse('agenda-detail-edit',
                                      kwargs={'pk': self.agenda_1.id}))
        self.assertRedirects(res, reverse('agenda-detail',
                                          kwargs={'pk':self.agenda_1.id}))

        # login as a user who's not the editor and try
        self.assertTrue(self.client.login(username='john',
                                          password='LSD'))
        res = self.client.get(reverse('agenda-detail-edit',
                                      kwargs={'pk': self.agenda_1.id}))
        self.assertRedirects(res, reverse('agenda-detail',
                                          kwargs={'pk':self.agenda_1.id}))

        # now login as the editor and try again
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.get(reverse('agenda-detail-edit',
                                      kwargs={'pk': self.agenda_1.id}))
        self.assertTemplateUsed(res,
                                'agendas/agenda_detail_edit.html')
        self.assertEqual(res.context['object'].id, self.agenda_1.id)
        self.assertEqual(res.context['object'].description, self.agenda_1.description)
        self.assertEqual(res.context['object'].public_owner_name, self.agenda_1.public_owner_name)
        self.assertEqual(list(res.context['object'].editors.all()), [self.user_1])

        # try to edit
        res = self.client.post(reverse('agenda-detail-edit',
                                       kwargs={'pk':self.agenda_1.id}),
                               {'name':'test1',
                                'public_owner_name':'test2',
                                'description': 'test3 description description' \
                                +'description'})
        self.assertEqual(res.status_code, 302)
        agenda = Agenda.objects.get(id=self.agenda_1.id)
        self.assertEqual(agenda.name, 'test1')

    def test_agenda_ascribe_meeting_not_logged_in(self):
        url = reverse('update-editors-agendas')
        res = self.client.post(url,
                               {'form-0-agenda_id':self.agenda_1.id,
                                'form-0-object_type':'committeemeeting',
                                'form-0-reasoning':'test reasoning',
                                'form-0-vote_id':self.meeting_1.id,
                                'form-0-weight':0.3,
                                'form-INITIAL_FORMS':1,
                                'form-MAX_NUM_FORMS':'',
                                'form-TOTAL_FORMS':1,
                               }
                              )
        self.assertRedirects(res, "%s?next=%s" % (settings.LOGIN_URL, url),
                             status_code=302)

    def test_agenda_ascribe_meeting_not_editor(self):
        self.assertTrue(self.client.login(username='john',
                                          password='LSD'))
        res = self.client.post(reverse('update-editors-agendas'),
                               {'form-0-agenda_id':self.agenda_1.id,
                                'form-0-object_type':'committeemeeting',
                                'form-0-reasoning':'test reasoning',
                                'form-0-vote_id':self.meeting_1.id,
                                'form-0-weight':0.3,
                                'form-INITIAL_FORMS':1,
                                'form-MAX_NUM_FORMS':'',
                                'form-TOTAL_FORMS':1,
                               }
                              )
        self.assertEqual(res.status_code, 403)


    def test_agenda_ascribe_meeting(self):
        self.assertTrue(self.client.login(username='jacob',
                                          password='JKM'))
        res = self.client.post(reverse('update-editors-agendas'),
                               {'form-0-agenda_id':self.agenda_1.id,
                                'form-0-object_type':'committeemeeting',
                                'form-0-reasoning':'test reasoning',
                                'form-0-vote_id':self.meeting_1.id,
                                'form-0-weight':0.3,
                                'form-INITIAL_FORMS':1,
                                'form-MAX_NUM_FORMS':'',
                                'form-TOTAL_FORMS':1,
                               }
                              )
        self.assertRedirects(res,
                             reverse('committee-meeting',
                                         kwargs={'pk':self.meeting_1.id}),
                             status_code=302)
        a = Agenda.objects.get(pk=self.agenda_1.id)
        self.assertEqual([am.meeting for am in a.agendameetings.all()],
                         [self.meeting_1])

    def test_agenda_ascribe_vote_not_logged_in(self):
        url = reverse('update-editors-agendas')
        res = self.client.post(url,
                               {'form-0-agenda_id':self.agenda_1.id,
                                'form-0-object_type':'vote',
                                'form-0-reasoning':'test reasoning',
                                'form-0-vote_id':self.vote_1.id,
                                'form-0-weight':1.0,
                                'form-INITIAL_FORMS':1,
                                'form-MAX_NUM_FORMS':'',
                                'form-TOTAL_FORMS':1,
                               }
                              )
        self.assertRedirects(res, "%s?next=%s" % (settings.LOGIN_URL, url),
                             status_code=302)

    def test_agenda_ascribe_vote_not_editor(self):
        self.assertTrue(self.client.login(username='john',
                                          password='LSD'))
        res = self.client.post(reverse('update-editors-agendas'),
                               {'form-0-agenda_id':self.agenda_1.id,
                                'form-0-object_type':'vote',
                                'form-0-reasoning':'test reasoning',
                                'form-0-vote_id':self.vote_1.id,
                                'form-0-weight':1.0,
                                'form-INITIAL_FORMS':1,
                                'form-MAX_NUM_FORMS':'',
                                'form-TOTAL_FORMS':1,
                               }
                              )
        self.assertEqual(res.status_code, 403)


    def test_agenda_ascribe_vote(self):
        self.assertTrue(self.client.login(username='jacob',
                                          password='JKM'))
        res = self.client.post(reverse('update-editors-agendas'),
                               {'form-0-agenda_id':self.agenda_1.id,
                                'form-0-object_type':'vote',
                                'form-0-reasoning':'test reasoning',
                                'form-0-vote_id':self.vote_1.id,
                                'form-0-weight':1.0,
                                'form-INITIAL_FORMS':1,
                                'form-MAX_NUM_FORMS':'',
                                'form-TOTAL_FORMS':1,
                               }
                              )
        self.assertRedirects(res,
                             reverse('vote-detail',
                                         kwargs={'object_id':self.meeting_1.id}),
                             status_code=302)
        av = AgendaVote.objects.get(agenda=self.agenda_1,
                                    vote=self.vote_1)
        self.assertEqual(av.score, 1.0)
        self.assertEqual(av.reasoning, 'test reasoning')

    def testAgendaMkDetail(self):
        res = self.client.get(reverse('mk-agenda-detail',
                                      kwargs={'pk': self.agenda_1.id,
                                              'member_id': self.mk_1.id}))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'agendas/mk_agenda_detail.html')
        self.assertEqual(int(res.context['score']), -33)
        self.assertEqual(len(res.context['related_votes']), 2)


    def tearDown(self):
        self.party_1.delete()
        self.mk_1.delete()
        self.user_1.delete()
        self.user_2.delete()
        self.user_3.delete()
        self.vote_1.delete()
        self.vote_2.delete()
        self.agenda_1.delete()
        self.agenda_2.delete()
        self.agenda_3.delete()

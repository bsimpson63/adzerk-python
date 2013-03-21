import json
import requests


API_KEY = ''


def set_key(key):
    import sys
    setattr(sys.modules[__name__], 'API_KEY', key)


class AdzerkError(Exception): pass
class NotFound(AdzerkError): pass


def handle_response(response):
    if response.status_code == 400:
        raise NotFound
    elif response.status_code != 200:
        raise AdzerkError('response %s' % response.status_code)
    try:
        return json.loads(response.text)
    except ValueError:
        raise AdzerkError('bad response')


goal_types = {
    1: 'Impressions',
    2: 'Percentage',
    3: 'Click',
    4: 'Even',
    5: 'View Conversions',
    6: 'Click Conversions',
    7: 'Any Conversions',
}

rate_types = {
    1: 'Flat',
    2: 'CPM',
    3: 'CPC',
    4: 'CPA View',
    5: 'CPA Click',
    6: 'CPA Both',
}

freq_cap_types = {
    1: 'Hour',
    2: 'Day',
}


class Base(object):
    _name = ''
    _base_url = 'http://api.adzerk.net/v1'
    _fields = {}
    _optional = set()

    @classmethod
    def _headers(cls):
        return {'X-Adzerk-ApiKey': API_KEY,
                'Content-Type': 'application/x-www-form-urlencoded'}

    def __init__(self, Id, **attr):
        self.Id = Id
        missing = self._fields - set(attr.keys()) - self._optional
        if missing:
            missing = ', '.join(missing)
            raise ValueError('missing required attributes: %s' % missing)
        extra = set(attr.keys()) - self._fields
        if extra:
            extra = ', '.join(extra)
            raise ValueError('unrecognized attributes: %s' % extra)

        for attr, val in attr.iteritems():
            setattr(self, attr, val)

    def __setattr__(self, attr, val):
        if attr not in self._fields and attr != 'Id':
            raise ValueError('unrecognized attribute: %s' % attr)
        object.__setattr__(self, attr, val)

    @classmethod
    def _from_item(cls, item):
        Id = item.pop('Id')
        thing = cls(Id, **item)
        return thing

    def _to_item(self):
        item = {'Id': self.Id}
        for attr in self._fields:
            if hasattr(self, attr):
                item[attr] = getattr(self, attr)
        return item

    def _to_data(self):
        return '%s=%s' % (self._name, json.dumps(self._to_item()))

    @classmethod
    def list(cls):
        url = '/'.join([cls._base_url, cls._name])
        response = requests.get(url, headers=cls._headers())
        content = handle_response(response)
        items = content.get('Items')
        if items:
            return [cls._from_item(item) for item in items]

    @classmethod
    def create(cls, **attr):
        url = '/'.join([cls._base_url, cls._name])
        thing = cls(None, **attr)
        data = thing._to_data()
        response = requests.post(url, headers=cls._headers(), data=data)
        item = handle_response(response)
        return cls._from_item(item)

    def _send(self):
        url = '/'.join([self._base_url, self._name, str(self.Id)])
        data = self._to_data()
        response = requests.put(url, headers=self._headers(), data=data)

    def update(self, **updates):
        url = '/'.join([self._base_url, self._name, str(self.Id)])
        originals = {}
        for attr, val in updates.iteritems():
            originals[attr] = getattr(self, attr)
            setattr(self, attr, val)
        data = self._to_data()
        response = requests.put(url, headers=self._headers(), data=data)
        try:
            item = handle_response(response)
        except AdzerkError:
            for attr, val in orignals.iteritems():
                setattr(self, attr, val)
            raise
        # return self? either modify self and don't return, or return new modified object

    @classmethod
    def get(cls, Id):
        url = '/'.join([cls._base_url, cls._name, str(Id)])
        response = requests.get(url, headers=cls._headers())
        item = handle_response(response)
        return cls._from_item(item)


class Map(Base):
    parent = None
    child = None

    @classmethod
    def list(cls, ParentId):
        url = '/'.join([cls._base_url, cls.parent._name, str(ParentId),
                        cls.child._name + 's'])
        response = requests.get(url, headers=cls._headers())
        content = handle_response(response)
        items = content.get('Items')
        if items:
            return [cls._from_item(item) for item in items]

    @classmethod
    def create(cls, ParentId, **attr):
        url = '/'.join([cls._base_url, cls.parent._name, str(ParentId),
                        cls.child._name])
        thing = cls(None, **attr)
        data = thing._to_data()
        response = requests.post(url, headers=cls._headers(), data=data)
        item = handle_response(response)
        return cls._from_item(item)

    @classmethod
    def get(cls, ParentId, Id):
        url = '/'.join([cls._base_url, cls.parent._name, str(ParentId),
                        cls.child._name, str(Id)])
        response = requests.get(url, headers=cls._headers())
        item = handle_response(response)
        return cls._from_item(item)


class Site(Base):
    _name = 'site'
    _fields = {'Url', 'Title', 'PublisherAccountId', 'IsDeleted'}
    _optional = {'PublisherAccountId'}

    def __repr__(self):
        return '<Site %s <%s-%s>>' % (self.Id, self.Title, self.Url)


class Zone(Base):
    _name = 'zone'
    _fields = {'Name', 'SiteId'}

    def __repr__(self):
        return '<Zone %s <%s on Site %s>>' % (self.Id, self.Name, self.SiteId)


class Advertiser(Base):
    _name = 'advertiser'
    _fields = {'Title', 'IsActive', 'IsDeleted'}
    _optional = {'IsActive', 'IsDeleted'}

    @classmethod
    def search(cls, Title):
        raise NotImplementedError

    def __repr__(self):
        return '<Advertiser %s <%s>>' % (self.Id, self.Title)


class Flight(Base):
    _name = 'flight'
    _fields = {'Name', 'StartDate', 'EndDate', 'NoEndDate', 'Price',
               'OptionType', 'Impressions', 'IsUnlimited', 'IsNoDuplicates',
               'IsFullSpeed', 'Keywords', 'UserAgentKeywords', 'CampaignId',
               'PriorityId', 'IsDeleted', 'IsActive', 'GoalType', 'RateType',
               'IsFreqCap', 'FreqCap', 'FreqCapDuration', 'FreqCapType',
               'DatePartingStartTime', 'DatePartingEndTime', 'IsSunday',
               'IsMonday', 'IsTuesday', 'IsWednesday', 'IsThursday', 'IsFriday',
               'IsSaturday', 'IPTargeting', 'GeoTargeting', 'CreativeMaps',
               'ReferrerKeywords', 'WeightOverride'}
    _optional = {'EndDate', 'NoEndDate', 'GoalType', 'RateType', 'IsFreqCap',
                 'FreqCap', 'FreqCapDuration', 'FreqCapType', 'Keywords',
                 'UserAgentKeywords', 'DatePartingStartTime',
                 'DatePartingEndTime', 'IsSunday', 'IsMonday', 'IsTuesday',
                 'IsWednesday', 'IsThursday', 'IsFriday', 'IsSaturday',
                 'IPTargeting', 'GeoTargeting', 'CreativeMaps',
                 'ReferrerKeywords', 'WeightOverride'}

    # list doesn't return CreativeMaps
    # _send from results of list doesn't work?

    @property
    def frequency_cap(self):
        if not self.IsFreqCap:
            return None
        return '%s per %s %s' % (self.FreqCap, self.FreqCapDuration,
                                 freq_cap_types[self.FreqCapType])

    def set_daily_cap(self, impressions):
        self.IsFreqCap = True
        self.FreqCapType = 2
        self.FreqCap = impressions
        self.FreqCapDuration = 1

    @classmethod
    def _from_item(cls, item):
        if not 'Name' in item:
            item['Name'] = ''   # response doesn't always include, is it optional?
        if not 'CreativeMaps' in item:
            item['CreativeMaps'] = []
        thing = super(cls, cls)._from_item(item)
        if hasattr(thing, 'CreativeMaps'):
            thing.CreativeMaps = [CreativeFlightMap._from_item(item)
                             for item in thing.CreativeMaps]
        return thing

    def _to_item(self):
        item = Base._to_item(self)
        cfm_things = item.get('CreativeMaps')
        if cfm_things:
            item['CreativeMaps'] = [thing._to_item() for thing in cfm_things]
        return item

    def __repr__(self):
        return '<Flight %s <Campaign %s>>' % (self.Id, self.CampaignId)


class Priority(Base):
    _name = 'priority'
    _fields = {'Name', 'ChannelId', 'Weight', 'IsDeleted'}

    def __repr__(self):
        return '<Priority %s <Weight %s - Channel %s>>' % (self.Id, self.Weight,
                                                           self.ChannelId)


class Creative(Base):
    _name = 'creative'
    _fields = {'Title', 'Body', 'Url', 'AdvertiserId', 'AdTypeId', 'ImageName',
               'Alt', 'IsHTMLJS', 'ScriptBody', 'IsSync', 'IsDeleted',
               'IsActive'}
    _optional = {'Url', 'ScriptBody', 'IsHTMLJS', 'ImageName'}

    @classmethod
    def list(cls, AdvertiserId):
        url = '/'.join([cls._base_url, 'advertiser', str(AdvertiserId),
                        'creatives'])
        response = requests.get(url, headers=cls._headers())
        content = handle_response(response)
        items = content.get('Items')
        if items:
            return [cls._from_item(item) for item in items]

    def __repr__(self):
        return '<Creative %s>' % (self.Id)


class CreativeFlightMap(Map):
    parent = Flight
    child = Creative

    _name = 'creative'
    _fields = {'SizeOverride', 'CampaignId', 'PublisherAccountId', 'IsDeleted',
               'Percentage', 'Iframe', 'Creative', 'IsActive', 'FlightId',
               'Impressions', 'SiteId', 'ZoneId', 'DistributionType'}
    _optional = {'SiteId', 'ZoneId'}

    @classmethod
    def _from_item(cls, item):
        if not 'SizeOverride' in item:
            item['SizeOverride'] = False    # response doesn't always include, is it optional?
        if not 'Iframe' in item:
            item['Iframe'] = False
        thing = super(cls, cls)._from_item(item)
        if hasattr(thing, 'Creative'):
            thing.Creative = Creative._from_item(thing.Creative)
        return thing

    def _to_item(self):
        item = Base._to_item(self)
        creative = item.get('Creative')
        if creative:
            if creative.Id:
                item['Creative'] = {'Id': creative.Id}
            else:
                item['Creative'] = creative._to_item()
        return item

    def __repr__(self):
        return '<CreativeFlightMap %s <Creative %s - Flight %s>>' % (
            self.Id,
            self.Creative.Id,
            self.FlightId,
        )


class Channel(Base):
    _name = 'channel'
    _fields = {'Title', 'Commission', 'Engine', 'Keywords', 'CPM', 'AdTypes',
               'IsDeleted'}

    def __repr__(self):
        return '<Channel %s>' % (self.Id)


class Publisher(Base):
    _name = 'publisher'
    _fields = {'FirstName', 'LastName', 'CompanyName', 'PaypalEmail',
               'PaymentOption', 'Address', 'IsDeleted'}
    _optional = {'FirstName', 'LastName', 'CompanyName', 'PaypalEmail',
                 'PaymentOption', 'Address'}
    # are these actually optional?
    # LastName, PaymentOption, PaypalEmail, FirstName, Address
    # undocumented IsDeleted

    def __repr__(self):
        return '<Publisher %s>' % (self.Id)


class Campaign(Base):
    _name = 'campaign'
    _fields = {'Name', 'AdvertiserId', 'Flights', 'StartDate', 'EndDate',
               'IsDeleted', 'IsActive', 'Price'}
    _optional = {'EndDate'}

    @classmethod
    def _from_item(cls, item):
        if not 'Flights' in item:
            item['Flights'] = []
        thing = super(cls, cls)._from_item(item)
        if hasattr(thing, 'Flights'):
            thing.Flights = [Flight._from_item(flight)
                             for flight in thing.Flights]
        return thing

    def _to_item(self):
        item = Base._to_item(self)
        flights = item.get('Flights')
        if flights:
            item['Flights'] = [flight._to_item() for flight in flights]
        return item

    def __repr__(self):
        return '<Campaign %s>' % (self.Id)

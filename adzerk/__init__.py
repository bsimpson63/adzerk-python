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


class Stub(object):
    def __init__(self, Id):
        self.Id = Id

    def _to_item(self):
        return {'Id': self.Id}


class Field(object):
    def __init__(self, name, optional=False):
        self.name = name
        self.optional = optional


class FieldSet(object):
    def __init__(self, *fields):
        self.fields = {field.name for field in fields}
        self.essentials = {field.name for field in fields if not field.optional}

    def to_set(self, exclude_optional=True):
        if exclude_optional:
            return self.essentials
        else:
            return self.fields

    def __iter__(self):
        for field_name in self.fields:
            yield field_name


class Base(object):
    _name = ''
    _base_url = 'http://api.adzerk.net/v1'
    _fields = FieldSet()

    @classmethod
    def _headers(cls):
        return {'X-Adzerk-ApiKey': API_KEY,
                'Content-Type': 'application/x-www-form-urlencoded'}

    def __init__(self, Id, **attr):
        self.Id = Id
        missing = self._fields.to_set() - set(attr.keys())
        if missing:
            missing = ', '.join(missing)
            raise ValueError('missing required attributes: %s' % missing)

        for attr, val in attr.iteritems():
            self.__setattr__(attr, val)

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
        item = {}
        if self.Id:
            item['Id'] = self.Id
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
        items = content.get('items')
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

    @classmethod
    def get(cls, Id):
        url = '/'.join([cls._base_url, cls._name, str(Id)])
        response = requests.get(url, headers=cls._headers())
        item = handle_response(response)
        return cls._from_item(item)


class Map(Base):
    parent = None
    parent_id_attr = 'ParentId'
    child = None

    @classmethod
    def list(cls, ParentId):
        url = '/'.join([cls._base_url, cls.parent._name, str(ParentId),
                        cls.child._name + 's'])
        response = requests.get(url, headers=cls._headers())
        content = handle_response(response)
        items = content.get('items')
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

    def _send(self):
        url = '/'.join([self._base_url, self.parent._name,
                        str(getattr(self, self.parent_id_attr)),
                        self.child._name, str(self.Id)])
        data = self._to_data()
        response = requests.put(url, headers=self._headers(), data=data)

    @classmethod
    def get(cls, ParentId, Id):
        url = '/'.join([cls._base_url, cls.parent._name, str(ParentId),
                        cls.child._name, str(Id)])
        response = requests.get(url, headers=cls._headers())
        item = handle_response(response)
        return cls._from_item(item)


class Site(Base):
    _name = 'site'
    _fields = FieldSet(
        Field('Url'),
        Field('Title'),
        Field('PublisherAccountId', optional=True),
        Field('IsDeleted'),
    )

    def __repr__(self):
        return '<Site %s <%s-%s>>' % (self.Id, self.Title, self.Url)


class Zone(Base):
    _name = 'zone'
    _fields = FieldSet(
        Field('Name'),
        Field('SiteId'),
    )

    def __repr__(self):
        return '<Zone %s <%s on Site %s>>' % (self.Id, self.Name, self.SiteId)


class Advertiser(Base):
    _name = 'advertiser'
    _fields = FieldSet(
        Field('Title'),
        Field('IsActive', optional=True),
        Field('IsDeleted', optional=True),
    )

    @classmethod
    def search(cls, Title):
        raise NotImplementedError

    def __repr__(self):
        return '<Advertiser %s <%s>>' % (self.Id, self.Title)


class Flight(Base):
    _name = 'flight'
    _fields = FieldSet(
        Field('Name'),
        Field('StartDate'),
        Field('EndDate', optional=True),
        Field('NoEndDate', optional=True),
        Field('Price'),
        Field('OptionType'),
        Field('Impressions'),
        Field('IsUnlimited'),
        Field('IsNoDuplicates', optional=True),
        Field('IsFullSpeed'),
        Field('Keywords', optional=True),
        Field('UserAgentKeywords', optional=True),
        Field('CampaignId'),
        Field('PriorityId'),
        Field('IsDeleted'),
        Field('IsActive'),
        Field('GoalType', optional=True),
        Field('RateType', optional=True),
        Field('IsFreqCap', optional=True),
        Field('FreqCap', optional=True),
        Field('FreqCapDuration', optional=True),
        Field('FreqCapType', optional=True),
        Field('DatePartingStartTime', optional=True),
        Field('DatePartingEndTime', optional=True),
        Field('IsSunday', optional=True),
        Field('IsMonday', optional=True),
        Field('IsTuesday', optional=True),
        Field('IsWednesday', optional=True),
        Field('IsThursday', optional=True),
        Field('IsFriday', optional=True),
        Field('IsSaturday', optional=True),
        Field('IPTargeting', optional=True),
        Field('GeoTargeting', optional=True),
        Field('SiteZoneTargeting', optional=True),  # Is this actually optional?
        Field('CreativeMaps', optional=True), # Not always included in adzerk response, should probably be a special stub to indicate that
        Field('ReferrerKeywords', optional=True),
        Field('WeightOverride', optional=True),
    )

    # list doesn't return CreativeMaps
    # _send from results of list doesn't work?
    # maybe need a _can_send property

    @classmethod
    def _from_item(cls, item):
        if not 'Name' in item:
            item['Name'] = ''   # response doesn't always include, is it optional?
        if not 'CreativeMaps' in item or not item['CreativeMaps']:
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
    _fields = FieldSet(
        Field('Name'),
        Field('ChannelId'),
        Field('Weight'),
        Field('IsDeleted'),
    )

    def __repr__(self):
        return '<Priority %s <Weight %s - Channel %s>>' % (self.Id, self.Weight,
                                                           self.ChannelId)


class Creative(Base):
    _name = 'creative'
    _fields = FieldSet(
        Field('Title'),
        Field('Body'),
        Field('Url', optional=True),
        Field('AdvertiserId'),
        Field('AdTypeId'),
        Field('ImageName', optional=True),
        Field('Alt'),
        Field('IsHTMLJS', optional=True),
        Field('ScriptBody', optional=True),
        Field('IsSync'),
        Field('IsDeleted'),
        Field('IsActive'),
    )

    @classmethod
    def list(cls, AdvertiserId):
        url = '/'.join([cls._base_url, 'advertiser', str(AdvertiserId),
                        'creatives'])
        response = requests.get(url, headers=cls._headers())
        content = handle_response(response)
        items = content.get('items')
        if items:
            return [cls._from_item(item) for item in items]

    def __repr__(self):
        return '<Creative %s>' % (self.Id)


class CreativeFlightMap(Map):
    parent = Flight
    parent_id_attr = 'FlightId'
    child = Creative

    _name = 'creative'
    _fields = FieldSet(
        Field('SizeOverride'),  # Not always included in adzerk response
        Field('CampaignId'),
        Field('PublisherAccountId'),
        Field('IsDeleted'),
        Field('Percentage'),
        Field('Iframe'), # Not always included in adzerk response
        Field('Creative'),
        Field('IsActive'),
        Field('FlightId'),
        Field('Impressions'),
        Field('SiteId', optional=True),
        Field('ZoneId', optional=True),
        Field('DistributionType'),
    )

    def __setattr__(self, attr, val):
        if attr == 'Creative':
            # Creative could be a full object or just a stub
            d = val
            Id = d.pop('Id')
            if d:
                val = Creative(Id, **d)
            else:
                val = Stub(Id)
        Map.__setattr__(self, attr, val)

    @classmethod
    def _from_item(cls, item):
        if not 'SizeOverride' in item:
            item['SizeOverride'] = False
        if not 'Iframe' in item:
            item['Iframe'] = False
        thing = super(cls, cls)._from_item(item)
        return thing

    def _to_item(self):
        item = Base._to_item(self)
        item['Creative'] = item['Creative']._to_item()
        return item

    def __repr__(self):
        return '<CreativeFlightMap %s <Creative %s - Flight %s>>' % (
            self.Id,
            self.Creative.Id,
            self.FlightId,
        )


class Channel(Base):
    _name = 'channel'
    _fields = FieldSet(
        Field('Title'),
        Field('Commission'), 
        Field('Engine'), 
        Field('Keywords'), 
        Field('CPM'), 
        Field('AdTypes'),
        Field('IsDeleted'),
    )

    def __repr__(self):
        return '<Channel %s>' % (self.Id)


class Publisher(Base):
    _name = 'publisher'
    _fields = FieldSet(
        Field('FirstName', optional=True),
        Field('LastName', optional=True),
        Field('CompanyName', optional=True),
        Field('PaypalEmail', optional=True),
        Field('PaymentOption', optional=True),
        Field('Address', optional=True),
        Field('IsDeleted'),
    )
    # are these actually optional?

    def __repr__(self):
        return '<Publisher %s>' % (self.Id)


class Campaign(Base):
    _name = 'campaign'
    _fields = FieldSet(
        Field('Name'),
        Field('AdvertiserId'),
        Field('Flights'),   # Not always included in adzerk response
        Field('StartDate'),
        Field('EndDate', optional=True),
        Field('IsDeleted'),
        Field('IsActive'),
        Field('Price'),
    )

    @classmethod
    def _from_item(cls, item):
        if not 'Flights' in item or not item['Flights']:
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


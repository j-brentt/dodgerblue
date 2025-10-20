[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/etkNZkSE)
CMPUT404-project-socialdistribution
===================================

CMPUT404-project-socialdistribution

See [the web page](https://uofa-cmput404.github.io/general/project.html) for a description of the project.

Make a distributed social network!

## License

MIT [License](LICENSE)

## Copyright

- Jax Yopek
- Jordan Brent
- Titobiloluwa Adeniji
- Zhikun Liu
- Botsian Liu
- Syed Shahmeer Rahman

# API Documentation

## GET /api/entries

  

### When to use

Use this endpoint to fetch all public entries from the node. Ideal for displaying public timelines, feeds, or any interface showing public content.

  

### How to use

- **HTTP Method:** GET

- **URL:** `http://service/api/entries/`

- **Authentication:** Optional

- **Query Parameters:**

- `page` (integer, optional): Page number to fetch. 

- `page_size` or `size` (integer, optional): Number of entries per page.

  

### Why / Why not

- **Why:** Retrieve all public content available on the node.

- **Why not:** Does not return private or friends-only entries. Not suitable for viewing restricted content.
  

### Examples

**Example 1: Get first 5 entries**

```http

GET http://service/api/entries/?page=1&page_size=5

```

  

Response:

```json

{

"count": 11,

"next": "http://service/api/entries/?page=2&page_size=5",

"previous": null,

"results": [

{

"type": "entry",

"id": "http://service/api/entries/130e95ca-fd2e-49ae-8844-9202021c38f5/",

"web": "http://service/entries/130e95ca-fd2e-49ae-8844-9202021c38f5/",

"title": "Sample Entry Title",

"description": "A brief description",

"content_type": "text/plain",

"content": "This is the entry content",

"visibility": "PUBLIC",

"published": "2025-10-17T17:19:52.114927Z",

"author": {

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "Sample Author",

"github": "https://github.com/sampleauthor",

"profileImage": "",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

}

]
... Four More Entries ...
}

```

  

**Example 2: Get all entries (no pagination params)**

```http

GET http://service/api/entries/

```
Response:

```json

{

"count": 11,

"next": "http://service/api/entries/?page=2&page_size=5",

"previous": null,

"results": [

{

"type": "entry",

"id": "http://service/api/entries/130e95ca-fd2e-49ae-8844-9202021c38f5/",

"web": "http://service/entries/130e95ca-fd2e-49ae-8844-9202021c38f5/",

"title": "Some spooky entry",

"description": "A brief yet scary description",

"content_type": "text/plain",

"content": "BOO!",

"visibility": "PUBLIC",

"published": "2025-10-17T17:19:52.114927Z",

"author": {

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "Sample Author (who sometimes writes horror short stories)",

"github": "https://github.com/sampleauthor",

"profileImage": "",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

}
... Nine More Entries (Defaults to 10 entries per page) ...
]
}

```
  

### Response Fields

- `count` (integer): Total number of entries available. Purpose: Shows how many total entries exist.

- `next` (string URL or null): URL to the next page of results. Purpose: Navigate to next page.

- `previous` (string URL or null): URL to the previous page of results.  Purpose: Navigate to previous page. 

- `results` (array): Array of entry objects. Purpose: Contains the actual entry data for the current page.

  

### Entry Object Fields (in results array)

- `type` (string): Object type identifier. Purpose: Identifies this as an entry object.

- `id` (string URL): Unique identifier for the entry. Purpose: Unique URL to access this specific entry.

- `web` (string URL): Frontend URL for viewing the entry. Purpose: URL for human-readable entry page.

- `title` (string): Entry title. Purpose: Display title of the entry.

- `description` (string): Brief description of the entry. Purpose: Provides summary of entry content.

- `content_type` (string): Content format type. Purpose: Indicates format (text/plain, text/markdown, image/png;base64, etc.).

- `content` (string): Main content of the entry. Purpose: The actual entry body/text/data.

- `visibility` (string): Visibility level. Purpose: Indicates who can see this entry (PUBLIC, FRIENDS, UNLISTED, DELETED).

- `published` Publication timestamp. Purpose: When the entry was created.

- `author` (object): Author information. Purpose: Identifies who created the entry.

  

### Author Object Fields (nested in entry)

- `type` (string): Object type identifier. Purpose: Identifies this as an author object.

- `id` (string URL): Unique identifier for the author.  Purpose: Unique URL to access author profile.

- `host` (string URL): API host URL. Purpose: Identifies the node where author is hosted.

- `displayName` (string): Author's display name. Purpose: Human-readable name for display.

- `github` (string URL or null): GitHub profile URL. Purpose: Link to author's GitHub profile.

- `profileImage` (string URL or empty): Profile image URL. Purpose: URL to author's profile picture.

- `web` (string URL): HTML profile page URL. Purpose: URL to author's human-readable profile page.

  

---

  

## GET /api/entries/{ENTRY_ID}

  

### When to use

Use this endpoint to fetch a specific entry by its ID. Use when displaying an individual entry detail page or retrieving a single entry.

  

### How to use

- **HTTP Method:** GET

- **URL:** `http://service/api/entries/{ENTRY_ID}/`

- **Authentication:** Optional for public entries

- **URL Parameters:**

- `ENTRY_ID` (string UUID): The unique identifier of the entry.

  

### Why / Why not

- **Why:** Access complete information about a specific entry.

- **Why not:** Cannot view deleted entries or entries you don't have permission to access.

  

### Examples

  

**Example 1: Get specific entry**

```http

GET http://service/api/entries/130e95ca-fd2e-49ae-8844-9202021c38f5/

```

  

Response:

```json

{

"type": "entry",

"id": "http://service/api/entries/130e95ca-fd2e-49ae-8844-9202021c38f5/",

"web": "http://service/entries/130e95ca-fd2e-49ae-8844-9202021c38f5/",

"title": "Sample Entry",

"description": "Entry description",

"content_type": "text/plain",

"content": "This is the entry content",

"visibility": "PUBLIC",

"published": "2025-10-17T17:19:52.114927Z",

"author": {

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "Sample Author",

"github": "https://github.com/sampleauthor",

"profileImage": "",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

}

```

  

**Example 2: Entry not found**

```http

GET http://service/api/entries/nonexistent-uuid/

```

  

Response: 404 Not Found

  

### Response Fields

Same as entry object fields from GET /api/entries (see above).

  

---

  

## GET /api/authors

  

### When to use

Use this endpoint to fetch all author profiles on the node. Use for displaying author lists or finding authors to follow.

  

### How to use

- **HTTP Method:** GET

- **URL:** `http://service/api/authors/`

- **Authentication:** Optional

- **Query Parameters:**

- `page` (integer, optional): Page number to fetch.
- `page_size` or `size` (integer, optional): Number of authors per page.

  

### Why / Why not

- **Why:** Discover all authors on the node.

- **Why not:** Shows all authors regardless of whether they have public content.


### Examples

  

**Example 1: Get first author**

```http

GET http://service/api/authors/?page=1&page_size=1

```

  

Response:

```json
\\ Shows one author (even though count = 3)
{

"count": 3,

"next": "http://service/api/authors/?page=2&page_size=1",

"previous": null,

"results": [

{

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "Sample Author",

"github": "https://github.com/sampleauthor",

"profileImage": "",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

]

}

```

  

**Example 2: Get all authors**

```http

GET http://service/api/authors/

```

Response:

```json
{

"count": 3,

"next": "http://service/api/authors/?page=2&page_size=1",

"previous": null,

"results": [

{

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef12345678666/",

"host": "http://service/api/",

"displayName": "Steve Jobs",

"github": "https://github.com/iPhone18Leaks",

"profileImage": "Steve Jobs Profile URL",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567666/"

}
... Two more authors (Note: count = 3)
]
}

```

### Response Fields

- `count` (integer): Total number of authors. Purpose: Shows how many authors exist on the node.

- `next` (string URL or null): URL to next page. Purpose: Navigate to next page.

- `previous` (string URL or null): URL to previous page. Purpose: Navigate to previous page.

- `results` (array): Array of author objects. Purpose: Contains author data for current page.

  

### Author Object Fields (in results array)

Same as author object fields from GET /api/entries (see above).

  

---

  

## GET /api/authors/{AUTHOR_ID}

  

### When to use

Use this endpoint to fetch a specific author's profile. Use when displaying an author profile page or getting author information.

  

### How to use

- **HTTP Method:** GET

- **URL:** `http://service/api/authors/{AUTHOR_ID}/`

- **Authentication:** Optional

- **URL Parameters:**

- `AUTHOR_ID` (string UUID): The unique identifier of the author.

  

### Why / Why not

- **Why:** Get detailed information about a specific author.

- **Why not:** Cannot modify author information with this endpoint (read-only).

  

### Examples

  

**Example 1: Get specific author**

```http

GET http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/

```

  

Response:

```json

{

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "Sample Arthur",

"github": "https://github.com/samplearthur",

"profileImage": "www.arthur.net",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

```

  

**Example 2: Author not found**

```http

GET http://service/api/authors/nonexistent-uuid/

```

  

Response: 404 Not Found

  

### Response Fields

Same as author object fields from GET /api/entries (see above).

  

---

  

## GET /api/authors/{AUTHOR_ID}/entries

  

### When to use

Use this endpoint to fetch all entries created by a specific author. Use for author profile pages, "My Entries" page, or author timelines.

  

### How to use

- **HTTP Method:** GET

- **URL:** `http://service/api/authors/{AUTHOR_ID}/entries/`

- **Authentication:** Optional (only public entries returned if not authenticated)

- **URL Parameters:**

- `AUTHOR_ID` (string UUID): The unique identifier of the author.

- **Query Parameters:**

- `page` (integer, optional): Page number to fetch.

- `page_size` or `size` (integer, optional): Number of entries per page.

  

### Why / Why not

- **Why:** Get all entries by a specific author.

- **Why not:** Only returns entries you have permission to view.


### Examples

  

**Example 1: Get author's entries**

```http

GET http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/entries/?page=1&page_size=5

```

  

Response:

```json

{

"count": 7,

"next": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/entries/?page=2&page_size=5",

"previous": null,

"results": [

{

"type": "entry",

"id": "http://service/api/entries/entry-uuid-here/",

"web": "http://service/entries/entry-uuid-here/",

"title": "My Entry Title",

"description": "Entry description",

"content_type": "text/plain",

"content": "Entry content here",

"visibility": "PUBLIC",

"published": "2025-10-17T13:00:00.000000Z",

"author": {

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "Sample Author",

"github": "https://github.com/sampleauthor",

"profileImage": "",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

}
... Four more entries (Note page_size=5)
]

}

```

  

**Example 2: Get all entries by author (no pagination)**

```http

GET http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/entries/

```
Response:


```json

{

"count": 7,

"next": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/entries/?page=2&page_size=5",

"previous": null,

"results": [

{

"type": "entry",

"id": "http://service/api/entries/entry-uuid-here/",

"web": "http://service/entries/entry-uuid-here/",

"title": "My Sad Entry Title",

"description": "I need to vent",

"content_type": "text/plain",

"content": "This project is rewarding but it can feel overwhelming sometimes.",

"visibility": "FRIENDS",

"published": "2025-10-17T13:00:00.000000Z",

"author": {

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "One of the devs",

"github": "https://github.com/notJaxYopek",

"profileImage": "",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

}
... Six more entries (Note: count=7) ...
]

}

```

  

### Response Fields

Same structure as GET /api/entries (see above for all field descriptions).

  

---

  

## POST /api/authors/{AUTHOR_ID}/entries

  

### When to use

Use this endpoint to create a new entry as the authenticated author. Use in "New Entry" submission forms or when programmatically creating content.

  

### How to use

- **HTTP Method:** POST

- **URL:** `http://service/api/authors/{AUTHOR_ID}/entries/`

- **Authentication:** Required (HTTP Basic Auth or session authentication)

- **URL Parameters:**

- `AUTHOR_ID` (string UUID): The unique identifier of the author creating the entry.

- **Headers:**

- `Content-Type: application/json`

- `Accept: application/json`

- `Authorization: Basic <credentials>` (if using Basic Auth)

  

### Why / Why not

- **Why:** Create content  via API.

- **Why not:** Can only create entries for the authenticated author's account.

  

### Examples

  

**Example 1: Create a text entry**

```http

POST http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/entries/

Content-Type: application/json

  

{

"title": "API Test Entry",

"description": "Testing entry creation",

"content_type": "text/plain",

"content": "This is a test entry created via the API",

"visibility": "PUBLIC"

}

```

  

Response (201 Created):

```json

{

"type": "entry",

"id": "http://service/api/entries/7e87768a-04cf-4011-bfe7-b3dd9fa431cf/",

"web": "http://service/entries/7e87768a-04cf-4011-bfe7-b3dd9fa431cf/",

"title": "API Test Entry",

"description": "Testing entry creation",

"content_type": "text/plain",

"content": "This is a test entry created via the API",

"visibility": "PUBLIC",

"published": "2025-10-17T22:36:05.039426Z",

"author": {

"type": "author",

"id": "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",

"host": "http://service/api/",

"displayName": "Sample Author",

"github": "https://github.com/sampleauthor",

"profileImage": "",

"web": "http://service/authors/profile/a1b2c3d4-e5f6-7890-abcd-ef1234567890/"

}

}

```

  


**Example 2: Using curl**

```bash

curl -X POST "http://service/api/authors/a1b2c3d4-e5f6-7890-abcd-ef1234567890/entries/" \

-u username:password \

-H "Content-Type: application/json" \

-H "Accept: application/json" \

-d '{

"title": "TV Show Rant",

"description": "What show I'm never going to finish even though everyone else has seen it",

"content_type": "text/plain",

"content": "Game of Thrones",

"visibility": "PUBLIC"

}'

```

  

### Request Fields

- `title` (string, required): Title of the entry. Purpose: Display title for the entry.

- `description` (string, optional): Brief description of entry. Purpose: Provides summary of entry.

- `content_type` (string, required): Format of the content. Purpose: Specifies content format (text/plain, text/markdown, image/png;base64, etc.).

- `content` (string, required): Main content of the entry. Purpose: The actual entry body/text/data.

- `visibility` (string, required): Who can see this entry. Purpose: Controls access (PUBLIC, FRIENDS, UNLISTED).

  

### Response Fields

Same as entry object fields from GET /api/entries (see above). Additionally returns HTTP status 201 Created on success.
